"""Busca dos bens no exterior (docs/adr/0018).

exterior_programa.DBK (gravado pelo programa com os 4 bens de exterior.json, todos nos EUA) faz o papel do
DBK com a declaração anterior: conta corrente (sem identificador), ações AAPL, BTC em corretora e fundo
não negociado (sem identificador).
"""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, identificar, identificar_linha
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

BENS = json.loads((DADOS / "exterior.json").read_text(encoding="utf-8"))["bens"]
CONTA, ACOES, BTC, FUNDO = BENS
EUA, ALEMANHA = "249", "023"


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "exterior_programa.DBK")


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def com(bem: dict, **mudancas) -> dict:
    return {**bem, **mudancas}


IMOVEL = {"grupo": "01", "codigo": "11", "pais": EUA, "discriminacao": "APARTAMENTO EM MIAMI",
          "situacao_anterior": "0.00", "situacao_atual": "100000.00",
          "imovel": {"logradouro": "Ocean Drive", "numero": "100", "area": "80.0", "unidade": "m2",
                     "data_aquisicao": "2020-01-10"}}


# --- chaves ---

def test_chaves():
    conta, acoes, btc, fundo, imovel = validados(CONTA, ACOES, BTC, FUNDO, IMOVEL)
    assert chave_busca(acoes) == ("03", "01", EUA, "AAPL")
    assert chave_busca(btc) == ("08", "01", "", "EXTERIOR", EUA)
    assert chave_busca(imovel) == ("01", "11", EUA, "OCEANDRIVE", "100")
    for sem in (conta, fundo):                                   # fundo não negociado, conta corrente
        identificacao = identificar(sem)
        assert identificacao.chave is None and identificacao.sem_identificador


def test_linhas_do_programa_tem_as_mesmas_chaves_do_json():
    linhas = {Registro27.DISCRIMINACAO.ler(l).rstrip(): l for l in dbk_do_programa().linhas_do_tipo(Registro27.TIPO)}
    for bem, campos in zip(BENS, validados(*BENS)):
        assert identificar_linha(linhas[bem["discriminacao"]]) == identificar(campos)


def test_imovel_com_endereco_escrito_de_outro_jeito_tem_a_mesma_chave():
    outro = com(IMOVEL, imovel={**IMOVEL["imovel"], "logradouro": "OCEAN  drive", "numero": "100"})
    assert chave_busca(validados(IMOVEL)[0]) == chave_busca(validados(outro)[0])


# --- com identificador ---

def test_acoes_e_btc_do_dbk_sao_atualizados():
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, com(ACOES, situacao_atual="1.00"), com(BTC, situacao_atual="2.00"))
    assert resultado.atualizados == [1, 2] and resultado.novos == [] and resultado.revisao == []


@pytest.mark.parametrize("bem", [com(ACOES, bolsa={"negociado": True, "codigo": "MSFT"}),
                                 com(ACOES, pais=ALEMANHA),
                                 com(BTC, pais=ALEMANHA)],
                         ids=["outro_codigo", "acao_em_outro_pais", "btc_em_outro_pais"])
def test_identificador_diferente_e_lancado_como_novo(bem):
    assert gravar(dbk_do_programa(), bem).novos == [1]


# --- sem identificador ---

@pytest.mark.parametrize("bem", [CONTA, FUNDO], ids=["conta", "fundo_nao_negociado"])
def test_sem_identificador_com_bem_igual_no_dbk_vai_para_revisao(bem, caplog):
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, bem)
    assert resultado.revisao == [1]
    assert arquivo.linhas == antes
    assert "sem campo identificador e o DBK já tem bem do mesmo grupo, código e país" in caplog.text


def test_sem_identificador_em_outro_pais_e_lancado_como_novo():
    assert gravar(dbk_do_programa(), com(CONTA, pais=ALEMANHA)).novos == [1]


def test_sem_identificador_sem_bem_igual_no_dbk_e_lancado_como_novo():
    vazio = ArquivoDBK([l for l in dbk_do_programa().linhas if l[:2] not in ("27", "37")])
    assert gravar(vazio, CONTA).novos == [1]


def test_acao_negociada_com_acao_sem_codigo_no_dbk_vai_para_revisao():
    """A ação do DBK pode ser a mesma, declarada antes como não negociada."""
    arquivo = dbk_do_programa()
    posicao = next(i for i in arquivo.indices(Registro27.TIPO)
                   if Registro27.DISCRIMINACAO.ler(arquivo.linhas[i]).startswith("ACOES"))
    linha = Registro27.BOLSA.gravar(arquivo.linhas[posicao], 0)
    linha = Registro27.COD_NEGOCIACAO.gravar(linha, "")
    arquivo.substituir(posicao, Registro27.gravar_cod_controle(linha))
    assert gravar(arquivo, ACOES).revisao == [1]


def test_relatorio_dos_bens_do_dbk_sem_identificador():
    resultado = gravar(dbk_do_programa(), com(ACOES, situacao_atual="1.00"))
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert texto.count("bem do exterior sem campo identificador: confira e atualize no programa") == 2
