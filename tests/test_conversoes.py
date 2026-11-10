"""Conversões genéricas do JSON para o formato do DBK."""

from decimal import Decimal

import pytest

from irpf_bot_2027.comum.conversoes import data_ddmmaaaa, numero, sim_nao, so_digitos, titular_dependente, valor_em_reais


@pytest.mark.parametrize(("entrada", "esperado"), [(True, 1), (False, 0)])
def test_sim_nao(entrada, esperado):
    assert sim_nao(entrada) == esperado


@pytest.mark.parametrize("entrada", ["nao", "true", 1, 0, None])
def test_sim_nao_recusa_o_que_nao_e_booleano(entrada):
    with pytest.raises(ValueError, match="esperado true ou false"):
        sim_nao(entrada)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("12.345.678/0001-99", "12345678000199"), ("123.456.789-00", "12345678900"), ("80000-000", "80000000")],
)
def test_so_digitos(entrada, esperado):
    assert so_digitos(entrada) == esperado


@pytest.mark.parametrize(("entrada", "esperado"), [("T", "T"), ("d", "D")])
def test_titular_dependente(entrada, esperado):
    assert titular_dependente(entrada) == esperado


def test_titular_dependente_recusa_outros_valores():
    with pytest.raises(ValueError, match='esperado "T" ou "D"'):
        titular_dependente("X")


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("2020-10-23", "23102020"), ("2019-03-05", "05032019")],
)
def test_data_vira_ddmmaaaa(entrada, esperado):
    assert data_ddmmaaaa(entrada) == esperado


@pytest.mark.parametrize("entrada", ["23/10/2020", "2020-02-30", ""])
def test_data_invalida_e_recusada(entrada):
    with pytest.raises(ValueError, match="AAAA-MM-DD"):
        data_ddmmaaaa(entrada)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("1234.56", Decimal("1234.56")), ("1000", Decimal("1000")), (1234.56, Decimal("1234.56")),
     (1000, Decimal("1000")), ("0.00", Decimal("0.00")), (" 10.5 ", Decimal("10.5"))],
    ids=["texto", "texto-sem-decimais", "numero-json", "inteiro-json", "zero", "espacos-nas-pontas"],
)
def test_valor_em_reais_aceito(entrada, esperado):
    assert valor_em_reais(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "trecho"),
    [
        ("1.234,56", "use ponto como separador decimal"),
        ("1234,56", "use ponto como separador decimal"),
        ("1,234.56", "use ponto como separador decimal"),
        ("R$ 100.00", "sem símbolo de moeda"),
        ("", "sem símbolo de moeda"),
        ("12.345", "no máximo 2 casa(s) decimal(is)"),
        (0.125, "no máximo 2 casa(s) decimal(is)"),
        ("-100.00", "não pode ser negativo"),
        (True, "esperado um número"),
        (None, "esperado um número"),
    ],
    ids=["virgula-e-milhar", "virgula", "milhar-americano", "moeda", "vazio", "tres-casas",
         "tres-casas-numero", "negativo", "booleano", "nulo"],
)
def test_valor_em_reais_recusado(entrada, trecho):
    with pytest.raises(ValueError) as erro:
        valor_em_reais(entrada)
    assert trecho in str(erro.value)


def test_mensagem_do_valor_nao_repete_o_valor():
    with pytest.raises(ValueError) as erro:
        valor_em_reais("98.765,43")
    assert "98" not in str(erro.value)


def test_negativo_so_quando_permitido():
    assert numero("-500.00", casas=2, permite_negativo=True) == Decimal("-500.00")


def test_area_com_uma_casa_decimal():
    assert numero("75.5", casas=1) == Decimal("75.5")
    with pytest.raises(ValueError, match="no máximo 1 casa"):
        numero("75.55", casas=1)
