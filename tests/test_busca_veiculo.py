"""Busca de veículo, aeronave e embarcação (02/01-03) pelo registro (docs/adr/0015).

veiculo_programa.DBK foi gravado pelo programa IRPF 2026 com os 5 bens de veiculo.json; aqui ele faz o
papel do DBK com a declaração anterior.
"""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, identificar_linha
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

BENS = json.loads((DADOS / "veiculo.json").read_text(encoding="utf-8"))["bens"]
CARRO, MOTO, CARRO_EXTERIOR, AERONAVE, LANCHA = BENS
OUTRO_RENAVAM = "00639456170"                       # válido pelo algoritmo do programa


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "veiculo_programa.DBK")


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


def com_registro(bem: dict, **veiculo) -> dict:
    return {**bem, "veiculo": veiculo}


# --- chave ---

def test_chaves():
    assert [chave_busca(c) for c in validados(*BENS)] == [
        ("02", "01", "105", "12345678900"),
        ("02", "01", "105", "987654322"),                      # gravado como 00987654322
        ("02", "01", "249", "ABC1234FL"),                      # gravado como 0ABC1234-FL
        ("02", "02", "105", "PTABC"),
        ("02", "03", "105", "1234567890"),
    ]


def test_linhas_do_programa_tem_as_mesmas_chaves_do_json():
    linhas = dbk_do_programa().linhas_do_tipo(Registro27.TIPO)
    assert [identificar_linha(l).chave for l in linhas] == [chave_busca(c) for c in validados(*BENS)]


# --- atualização ---

def test_todos_os_bens_do_dbk_sao_atualizados():
    arquivo = dbk_do_programa()
    novos_valores = ["1.00", "2.00", "3.00", "4.00", "5.00"]
    resultado = gravar(arquivo, *[{**bem, "situacao_atual": v} for bem, v in zip(BENS, novos_valores)])
    assert resultado.atualizados == [1, 2, 3, 4, 5]
    assert resultado.novos == [] and resultado.revisao == [] and resultado.nao_informados == []
    for bem, valor in zip(BENS, novos_valores):
        assert Registro27.VALOR_ATUAL.ler(linha_de(arquivo, bem["discriminacao"])) == Registro27.VALOR_ATUAL.formatar(valor)


@pytest.mark.parametrize("bem", [com_registro(MOTO, renavam="00987654322"),
                                 com_registro(AERONAVE, registro_aeronave="pt abc"),
                                 com_registro(CARRO_EXTERIOR, renavam="abc1234fl")],
                         ids=["renavam_com_zeros", "aeronave_sem_hifen", "exterior_sem_hifen"])
def test_mesmo_registro_escrito_de_outro_jeito_e_encontrado(bem):
    assert gravar(dbk_do_programa(), bem).atualizados == [1]


@pytest.mark.parametrize("bem", [com_registro(CARRO, renavam=OUTRO_RENAVAM),
                                 {**CARRO_EXTERIOR, "pais": "023"},
                                 com_registro(LANCHA, registro_embarcacao="999")],
                         ids=["outro_renavam", "outro_pais", "outra_embarcacao"])
def test_registro_diferente_e_lancado_como_novo(bem):
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, bem)
    assert resultado.novos == [1]
    assert len(arquivo.linhas_do_tipo(Registro27.TIPO)) == 6


# --- registro em branco ---

def test_renavam_em_branco_no_dbk_manda_o_carro_do_json_para_revisao():
    arquivo = dbk_do_programa()
    alterar(arquivo, "CARRO RENAVAM 11 DIGITOS", RENAVAM="")
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, com_registro(CARRO, renavam=OUTRO_RENAVAM))
    assert resultado.revisao == [1]
    assert arquivo.linhas == antes
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "dados da chave em branco ou fora do formato no DBK" in texto


def test_veiculo_sem_registro_no_exterior_nao_bloqueia_os_do_brasil():
    arquivo = dbk_do_programa()
    alterar(arquivo, "CARRO NO EXTERIOR", RENAVAM="")
    resultado = gravar(arquivo, com_registro(CARRO, renavam=OUTRO_RENAVAM))
    assert resultado.novos == [1]


def test_veiculo_do_json_sem_registro_no_exterior_e_lancado_como_novo():
    arquivo = dbk_do_programa()
    sem_registro = {k: v for k, v in CARRO_EXTERIOR.items() if k != "veiculo"}
    resultado = gravar(arquivo, sem_registro)
    assert resultado.novos == [1]
