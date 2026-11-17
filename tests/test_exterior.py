"""Bloco exterior: lucro ou prejuízo e imposto da aplicação financeira, lucros e dividendos recebidos e
imposto sobre eles (docs/adr/0017).

exterior_programa.DBK foi gravado pelo programa IRPF 2026 em 17/11/2026 com os mesmos 4 bens de
exterior.json, digitados na tela (CPF fictício). O programa também gravou as linhas 24 e 37, que ele
calcula a partir da 27 e o bot não grava.
"""

import json
import logging

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.ficha import montar_linha
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CPF = "77039677008"
BENS = json.loads((DADOS / "exterior.json").read_text(encoding="utf-8"))["bens"]
LINHAS = [linha for linha in ler_linhas(DADOS / "exterior_programa.DBK") if linha.startswith("27")]
CONTA, ACOES, BTC, FUNDO = BENS


def linha_do_programa(bem: dict) -> str:
    [linha] = [l for l in LINHAS if Registro27.DISCRIMINACAO.ler(l).rstrip() == bem["discriminacao"]]
    return linha


def com_exterior(bem: dict, **exterior) -> dict:
    return {**bem, "exterior": exterior}


@pytest.mark.parametrize("bem", BENS, ids=[bem["discriminacao"] for bem in BENS])
def test_linha_igual_a_gravada_pelo_programa(bem):
    campos, erros = validar_bem(bem)
    assert erros == []
    esperada = linha_do_programa(bem)
    assert montar_linha(bem, campos, CPF, int(Registro27.CHAVE.ler(esperada))) == esperada


def test_prejuizo_gravado_com_sinal():
    campos, _ = validar_bem(ACOES)
    assert Registro27.AF_RENDIMENTO.ler(montar_linha(ACOES, campos, CPF, 1)) == "-000000025000"


@pytest.mark.parametrize("chave", ["imposto_pago", "dividendos_recebidos", "imposto_dividendos"])
def test_so_o_lucro_ou_prejuizo_aceita_negativo(chave):
    _, erros = validar_bem(com_exterior(ACOES, **{chave: "-1.00"}))
    assert erros == [f"'exterior.{chave}': o valor não pode ser negativo"]


def test_conta_no_exterior_nao_tem_lucros_e_dividendos():
    _, erros = validar_bem(com_exterior(CONTA, dividendos_recebidos="10.00"))
    assert erros == ["'exterior.dividendos_recebidos' não se aplica a 06/01 (Depósito em conta corrente "
                     "ou conta pagamento) no exterior"]


def test_bloco_exterior_em_bem_no_brasil():
    contas = json.loads((DADOS / "contas.json").read_text(encoding="utf-8"))["bens"]
    _, erros = validar_bem(com_exterior(contas[0], lucro_prejuizo="1.00"))
    assert erros == ["'exterior.lucro_prejuizo' não se aplica a 06/01 (Depósito em conta corrente "
                     "ou conta pagamento) no Brasil"]


def test_bloco_exterior_e_opcional():
    _, erros = validar_bem({k: v for k, v in FUNDO.items() if k != "exterior"})
    assert erros == []


def test_valor_com_virgula_e_recusado():
    _, erros = validar_bem(com_exterior(CONTA, lucro_prejuizo="100,00"))
    assert erros == ["'exterior.lucro_prejuizo': use ponto como separador decimal, sem separador de milhar: \"1234.56\""]


# --- bem encontrado: os valores do ano são sempre os do JSON ---

BTC_AUTO = {"grupo": "08", "codigo": "01", "pais": "249", "discriminacao": "BTC EM CARTEIRA PROPRIA",
            "situacao_anterior": "0.00", "situacao_atual": "1000.00", "cripto": {"autocustodiante": True},
            "exterior": {"lucro_prejuizo": "100.00", "imposto_pago": "10.00"}}


def gravar(arquivo, *lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return bens.inserir(arquivo, list(lista), campos)


def dbk_com_btc() -> ArquivoDBK:
    """DBK sem bens + o BTC autocustodiante no exterior (único bem do exterior com busca)."""
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    arquivo = ArquivoDBK([l for l in arquivo.linhas if l[:2] not in ("27", "37")], arquivo.quebra_no_fim)
    gravar(arquivo, BTC_AUTO)
    return ArquivoDBK(list(arquivo.linhas), arquivo.quebra_no_fim)


def test_valores_do_ano_do_json_substituem_os_do_dbk(caplog):
    arquivo = dbk_com_btc()
    with caplog.at_level(logging.INFO):
        resultado = gravar(arquivo, com_exterior(BTC_AUTO, lucro_prejuizo="-30.00", imposto_pago="0.00"))
    assert resultado.atualizados == [1] and resultado.conferir == []
    [linha] = arquivo.linhas_do_tipo(Registro27.TIPO)
    assert Registro27.AF_RENDIMENTO.ler(linha) == "-000000003000"
    assert Registro27.AF_IMPOSTO.ler(linha) == "0000000000000"
    assert "valores do ano no exterior gravados: exterior.imposto_pago, exterior.lucro_prejuizo" in caplog.text
    assert Registro27.gravar_cod_controle(linha) == linha


def test_sem_o_bloco_os_valores_do_dbk_ficam():
    arquivo = dbk_com_btc()
    resultado = gravar(arquivo, {k: v for k, v in BTC_AUTO.items() if k != "exterior"})
    assert resultado.atualizados == [1]
    [linha] = arquivo.linhas_do_tipo(Registro27.TIPO)
    assert Registro27.AF_RENDIMENTO.ler(linha) == "0000000010000"
