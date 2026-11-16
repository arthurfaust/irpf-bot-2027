"""Busca de poupança (04/01) e conta corrente (06/01): grupo + código + banco + agência + conta
(docs/adr/0011).

contas_programa.DBK foi gravado pelo programa IRPF 2026 com os 6 bens de contas.json; aqui ele faz o
papel do DBK com a declaração anterior.
"""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, identificar_linha
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CONTAS = json.loads((DADOS / "contas.json").read_text(encoding="utf-8"))["bens"]
BB, CAIXA_POUPANCA, CAIXA_CORRENTE, ITAU_CORRENTE, ITAU_POUPANCA, NUBANK = CONTAS


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "contas_programa.DBK")


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def com_valor(bem: dict, atual: str) -> dict:
    return {**bem, "situacao_atual": atual}


def com_conta(bem: dict, **conta) -> dict:
    return {**bem, "conta": {**bem["conta"], **conta}}


def alterar_linha_da_conta(arquivo: ArquivoDBK, indice: int, **campos) -> None:
    """Muda campos da linha 27 de número `indice` (0 = primeira) e regrava o controle."""
    posicao = arquivo.indices(Registro27.TIPO)[indice]
    linha = arquivo.linhas[posicao]
    for nome, valor in campos.items():
        linha = getattr(Registro27, nome).gravar(linha, valor)
    arquivo.substituir(posicao, Registro27.gravar_cod_controle(linha))


# --- chave ---

def test_chave_da_conta():
    assert [chave_busca(c) for c in validados(*CONTAS)] == [
        ("06", "01", "1", "1234", "98765"),
        ("04", "01", "104", "567", "4321"),
        ("06", "01", "104", "567", "123456789"),
        ("06", "01", "341", "350", "11223"),
        ("04", "01", "341", "350", "11223"),
        ("06", "01", "260", "1", "7654321"),
    ]


def test_linha_gravada_pelo_programa_tem_a_mesma_chave_do_json():
    linhas = dbk_do_programa().linhas_do_tipo(Registro27.TIPO)
    assert [identificar_linha(l).chave for l in linhas] == [chave_busca(c) for c in validados(*CONTAS)]


def test_poupanca_e_corrente_com_o_mesmo_numero_tem_chaves_diferentes():
    corrente, poupanca = validados(ITAU_CORRENTE, ITAU_POUPANCA)
    assert chave_busca(corrente) != chave_busca(poupanca)


# --- atualização ---

def test_todas_as_contas_do_dbk_sao_atualizadas():
    arquivo = dbk_do_programa()
    anteriores = [Registro27.VALOR_ANTERIOR.ler(l) for l in arquivo.linhas_do_tipo(Registro27.TIPO)]
    novos_valores = ["11.00", "22.00", "33.00", "44.00", "55.00", "66.00"]

    resultado = gravar(arquivo, *[com_valor(bem, v) for bem, v in zip(CONTAS, novos_valores)])

    assert resultado.atualizados == [1, 2, 3, 4, 5, 6]
    assert resultado.novos == [] and resultado.revisao == [] and resultado.nao_informados == []
    linhas = arquivo.linhas_do_tipo(Registro27.TIPO)
    assert [Registro27.VALOR_ATUAL.ler(l) for l in linhas] == [
        Registro27.VALOR_ATUAL.formatar(v) for v in novos_valores]
    assert [Registro27.VALOR_ANTERIOR.ler(l) for l in linhas] == anteriores
    assert all(Registro27.gravar_cod_controle(l) == l for l in linhas)


def test_poupanca_do_itau_nao_atualiza_a_corrente():
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, com_valor(ITAU_POUPANCA, "999.00"))
    linhas = arquivo.linhas_do_tipo(Registro27.TIPO)
    assert resultado.atualizados == [1]
    assert Registro27.VALOR_ATUAL.ler(linhas[4]) == Registro27.VALOR_ATUAL.formatar("999.00")
    assert Registro27.VALOR_ATUAL.ler(linhas[3]) == Registro27.VALOR_ATUAL.formatar("450.00")    # corrente intacta


def test_conta_da_caixa_sem_zeros_no_dbk_e_encontrada():
    """Restaurada no programa, a conta pode voltar sem os zeros à esquerda (docs/adr/0010)."""
    arquivo = dbk_do_programa()
    alterar_linha_da_conta(arquivo, 1, CONTA="4321")
    resultado = gravar(arquivo, CAIXA_POUPANCA)
    assert resultado.atualizados == [1]


def test_agencia_com_zeros_a_esquerda_no_json_e_encontrada():
    resultado = gravar(dbk_do_programa(), com_conta(ITAU_CORRENTE, agencia="350"))
    assert resultado.atualizados == [1]


@pytest.mark.parametrize("alteracao", [{"agencia": "9999"}, {"conta": "11224"}, {"banco": "237"}],
                         ids=["outra_agencia", "outra_conta", "outro_banco"])
def test_conta_diferente_e_lancada_como_nova(alteracao):
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, com_conta(ITAU_CORRENTE, **alteracao))
    assert resultado.novos == [1] and resultado.atualizados == []
    assert len(arquivo.linhas_do_tipo(Registro27.TIPO)) == 7


def test_conta_da_caixa_com_operacao_no_json_nao_casa_com_a_do_dbk_sem_operacao():
    """Limitação conhecida (docs/adr/0011): a operação na frente muda a conta."""
    arquivo = dbk_do_programa()
    chave_da_poupanca = int(Registro27.CHAVE.ler(arquivo.linhas_do_tipo(Registro27.TIPO)[1]))
    resultado = gravar(arquivo, com_conta(CAIXA_POUPANCA, conta="01300004321"))
    assert resultado.novos == [1]
    assert chave_da_poupanca in [bem.chave for bem in resultado.nao_informados]     # aparece no relatório


# --- chave incompleta ou fora do formato no DBK ---

@pytest.mark.parametrize("campos", [{"CONTA": "98765-X"}, {"CONTA": ""}, {"BANCO": 0}, {"AGENCIA": 0}],
                         ids=["conta_com_dv", "conta_em_branco", "banco_em_branco", "agencia_em_branco"])
def test_conta_incompleta_no_dbk_manda_o_bem_do_json_para_revisao(campos):
    arquivo = dbk_do_programa()
    alterar_linha_da_conta(arquivo, 0, **campos)                 # a corrente do BB
    antes = list(arquivo.linhas)

    resultado = gravar(arquivo, BB)

    assert resultado.revisao == [1]
    assert arquivo.linhas == antes
    incompletos = [b for b in resultado.nao_informados if b.chave_incompleta]
    assert [(b.grupo, b.codigo) for b in incompletos] == [("06", "01")]
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "dados da chave em branco ou fora do formato no DBK" in texto


def test_conta_incompleta_de_outro_codigo_nao_bloqueia():
    arquivo = dbk_do_programa()
    alterar_linha_da_conta(arquivo, 1, CONTA="")                 # a poupança da Caixa (04/01)
    resultado = gravar(arquivo, BB)                              # conta corrente (06/01)
    assert resultado.atualizados == [1]
