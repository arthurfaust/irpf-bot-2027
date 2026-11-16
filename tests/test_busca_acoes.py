"""Busca de ações (03/01) e de ativos negociados em bolsa (04/04) (docs/adr/0013).

bolsa_programa.DBK foi gravado pelo programa IRPF 2026 com os 6 bens de bolsa.json; aqui ele faz o
papel do DBK com a declaração anterior.
"""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, identificar_linha
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

BENS = json.loads((DADOS / "bolsa.json").read_text(encoding="utf-8"))["bens"]
PETR4, PETR3, FECHADA, FII, FII_13, BDR = BENS
PETROBRAS = "33000167000101"


def dbk_do_programa(sem: tuple[str, ...] = ()) -> ArquivoDBK:
    """O DBK do programa, opcionalmente sem as linhas 27 com essas discriminações."""
    arquivo = ArquivoDBK.ler(DADOS / "bolsa_programa.DBK")
    linhas = [l for l in arquivo.linhas
              if not (l.startswith("27") and Registro27.DISCRIMINACAO.ler(l).rstrip() in sem)]
    return ArquivoDBK(linhas, arquivo.quebra_no_fim)


def linha_de(arquivo: ArquivoDBK, discriminacao: str) -> str:
    [linha] = [l for l in arquivo.linhas_do_tipo(Registro27.TIPO)
               if Registro27.DISCRIMINACAO.ler(l).rstrip() == discriminacao]
    return linha


def alterar(arquivo: ArquivoDBK, discriminacao: str, **campos) -> None:
    posicao = arquivo.linhas.index(linha_de(arquivo, discriminacao))
    linha = arquivo.linhas[posicao]
    for nome, valor in campos.items():
        linha = getattr(Registro27, nome).gravar(linha, valor)
    arquivo.substituir(posicao, Registro27.gravar_cod_controle(linha))


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def com(bem: dict, **mudancas) -> dict:
    return {**bem, **mudancas}


def valor_atual(arquivo: ArquivoDBK, discriminacao: str) -> str:
    return Registro27.VALOR_ATUAL.ler(linha_de(arquivo, discriminacao))


# --- chave ---

def test_chaves():
    petr4, petr3, fechada, bdr = validados(PETR4, PETR3, FECHADA, BDR)
    assert chave_busca(petr4) == ("03", "01", PETROBRAS, "PETR4")
    assert chave_busca(petr3) == ("03", "01", PETROBRAS, "PETR3")
    assert chave_busca(fechada) == ("03", "01", "11222333000181", "")         # não negociada: sem código
    assert chave_busca(bdr) == ("04", "04", "AAPL34")                           # veio "aapl34" no JSON


def test_linhas_do_programa_tem_as_mesmas_chaves_do_json():
    arquivo = dbk_do_programa()
    for bem in (PETR4, PETR3, FECHADA, BDR):
        [campos] = validados(bem)
        assert identificar_linha(linha_de(arquivo, bem["discriminacao"])).chave == chave_busca(campos)


@pytest.mark.parametrize("bem", [com(PETR4, pais="249", cnpj_cpf=None), com(BDR, bolsa={"negociado": False})],
                         ids=["acao_no_exterior", "bdr_nao_negociado"])
def test_sem_busca(bem):
    bem = {k: v for k, v in bem.items() if v is not None}
    assert chave_busca(validados(bem)[0]) is None


# --- atualização ---

def test_acoes_e_bdr_do_dbk_sao_atualizados():
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, com(PETR4, situacao_atual="11.00"), com(PETR3, situacao_atual="22.00"),
                       com(FECHADA, situacao_atual="33.00"), com(BDR, situacao_atual="44.00"))
    assert resultado.atualizados == [1, 2, 3, 4]
    assert resultado.novos == [] and resultado.revisao == []
    for bem, valor in ((PETR4, "11.00"), (PETR3, "22.00"), (FECHADA, "33.00"), (BDR, "44.00")):
        assert valor_atual(arquivo, bem["discriminacao"]) == Registro27.VALOR_ATUAL.formatar(valor)
    # os dois FII (mesmo CNPJ) ficaram de fora e aparecem no relatório
    assert len(resultado.nao_informados) == 2


def test_on_nao_atualiza_a_pn():
    arquivo = dbk_do_programa()
    gravar(arquivo, com(PETR3, situacao_atual="999.00"))
    assert valor_atual(arquivo, "ACOES PETROBRAS ON") == Registro27.VALOR_ATUAL.formatar("999.00")
    assert valor_atual(arquivo, "ACOES PETROBRAS PN") == Registro27.VALOR_ATUAL.formatar("1200.00")


def test_acao_de_outra_empresa_e_lancada_como_nova():
    resultado = gravar(dbk_do_programa(), com(PETR4, cnpj_cpf="11.444.777/0001-61", bolsa={"negociado": True, "codigo": "ABCD3"}))
    assert resultado.novos == [1]


def test_bdr_com_outro_codigo_e_lancado_como_novo():
    resultado = gravar(dbk_do_programa(), com(BDR, bolsa={"negociado": True, "codigo": "MSFT34"}))
    assert resultado.novos == [1]


# --- mesmo CNPJ com outro código (família) ---

def test_pn_nova_com_a_on_no_dbk_vai_para_revisao():
    """O DBK só tem a PETR3; a PETR4 do JSON pode ser compra nova ou a mesma ação com outro código."""
    arquivo = dbk_do_programa(sem=("ACOES PETROBRAS PN",))
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, PETR4)
    assert resultado.revisao == [1]
    assert arquivo.linhas == antes


def test_acao_declarada_antes_como_nao_negociada_vai_para_revisao():
    arquivo = dbk_do_programa(sem=("ACOES PETROBRAS ON",))
    alterar(arquivo, "ACOES PETROBRAS PN", BOLSA=0, COD_NEGOCIACAO="")
    resultado = gravar(arquivo, PETR4)
    assert resultado.revisao == [1]


def test_negociada_com_codigo_em_branco_no_dbk_e_chave_incompleta():
    arquivo = dbk_do_programa()
    alterar(arquivo, "ACOES PETROBRAS PN", COD_NEGOCIACAO="")
    resultado = gravar(arquivo, PETR4)
    assert resultado.revisao == [1]
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "dados da chave em branco ou fora do formato no DBK" in texto


def test_familia_de_outro_cnpj_nao_bloqueia():
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, com(FECHADA, cnpj_cpf="11.444.777/0001-61"))     # outra empresa fechada
    assert resultado.novos == [1]


# --- fundos: a chave continua grupo + CNPJ (docs/adr/0006) ---

def test_fii_com_dois_codigos_no_mesmo_cnpj_vai_para_revisao():
    """Limitação conhecida: o código de negociação não entra na chave dos fundos."""
    resultado = gravar(dbk_do_programa(), FII)
    assert resultado.revisao == [1]
