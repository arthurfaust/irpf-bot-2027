"""Bloco bolsa: "Negociados em Bolsa?" e código de negociação.

bolsa_programa.DBK foi gravado pelo programa IRPF 2026 em 16/11/2026 com os mesmos 6 bens de
bolsa.json, digitados na tela (CPF fictício). No JSON, o código do BDR vem em minúsculas de propósito.
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.fichas.bens.ficha import montar_linha
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CPF = "77039677008"
BENS = json.loads((DADOS / "bolsa.json").read_text(encoding="utf-8"))["bens"]
LINHAS = [linha for linha in ler_linhas(DADOS / "bolsa_programa.DBK") if linha.startswith("27")]
PETR4, PETR3, FECHADA, FII, FII_13, BDR = BENS


def linha_do_programa(bem: dict) -> str:
    """A linha do programa com a mesma discriminação (o programa reordena os bens no arquivo)."""
    [linha] = [l for l in LINHAS if Registro27.DISCRIMINACAO.ler(l).rstrip() == bem["discriminacao"]]
    return linha


def com_bolsa(bem: dict, **bolsa) -> dict:
    """Cópia do bem com o bloco bolsa trocado (sem argumentos, remove o bloco)."""
    novo = {k: v for k, v in bem.items() if k != "bolsa"}
    return {**novo, "bolsa": bolsa} if bolsa else novo


@pytest.mark.parametrize("bem", BENS, ids=[bem["discriminacao"] for bem in BENS])
def test_linha_igual_a_gravada_pelo_programa(bem):
    campos, erros = validar_bem(bem)
    assert erros == []
    esperada = linha_do_programa(bem)
    assert montar_linha(bem, campos, CPF, int(Registro27.CHAVE.ler(esperada))) == esperada


@pytest.mark.parametrize("bem", [PETR4, FII, BDR], ids=["acoes", "fii", "bdr"])
def test_pergunta_negociado_em_bolsa_e_obrigatoria(bem):
    _, erros = validar_bem(com_bolsa(bem))
    assert len(erros) == 1 and erros[0].startswith("'bolsa.negociado' é obrigatório para ")


def test_codigo_e_obrigatorio_quando_negociado():
    _, erros = validar_bem(com_bolsa(PETR4, negociado=True))
    assert erros == ["'bolsa.codigo' é obrigatório para 03/01 (Ações (inclusive as listadas em bolsa)) no Brasil"]


def test_codigo_nao_se_aplica_quando_nao_negociado():
    _, erros = validar_bem(com_bolsa(FECHADA, negociado=False, codigo="ABCD3"))
    assert erros == ["'bolsa.codigo' não se aplica a 03/01 (Ações (inclusive as listadas em bolsa)) no Brasil"]


def test_nao_negociado_grava_zero_e_codigo_em_branco():
    campos, _ = validar_bem(FECHADA)
    linha = montar_linha(FECHADA, campos, CPF, 1)
    assert Registro27.BOLSA.ler(linha) == "0"
    assert Registro27.COD_NEGOCIACAO.ler(linha).strip() == ""


def test_codigo_vai_em_maiusculas():
    campos, _ = validar_bem(BDR)
    assert campos["COD_NEGOCIACAO"] == "AAPL34"


@pytest.mark.parametrize(
    ("codigo", "erro"),
    [
        ("ABCDEFGHIJK123", "'bolsa.codigo': o código de negociação tem no máximo 13 caracteres"),
        ("PETR 4", "'bolsa.codigo': esperado o código de negociação só com letras e números (ex.: \"PETR4\")"),
        ("PETR-4", "'bolsa.codigo': esperado o código de negociação só com letras e números (ex.: \"PETR4\")"),
        (4, "'bolsa.codigo': esperado o código de negociação só com letras e números (ex.: \"PETR4\")"),
    ],
)
def test_codigo_invalido(codigo, erro):
    _, erros = validar_bem(com_bolsa(PETR4, negociado=True, codigo=codigo))
    assert erros == [erro]


def test_negociado_precisa_ser_true_ou_false():
    _, erros = validar_bem(com_bolsa(PETR4, negociado="sim", codigo="PETR4"))
    assert erros == ["'bolsa.negociado': esperado true ou false, veio 'sim'"]


def test_codigo_sem_a_pergunta_acusa_so_a_pergunta():
    _, erros = validar_bem(com_bolsa(PETR4, codigo="PETR4"))
    assert erros == ["'bolsa.negociado' é obrigatório para 03/01 (Ações (inclusive as listadas em bolsa)) no Brasil"]


def test_bloco_bolsa_em_bem_sem_a_pergunta():
    poupanca = {**json.loads((DADOS / "contas.json").read_text(encoding="utf-8"))["bens"][1],
                "bolsa": {"negociado": False}}
    _, erros = validar_bem(poupanca)
    assert erros == ["'bolsa.negociado' não se aplica a 04/01 (Depósito em conta poupança) no Brasil"]
