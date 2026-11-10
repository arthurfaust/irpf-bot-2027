"""Conversões genéricas do JSON para o formato do DBK."""

import pytest

from irpf_bot_2027.comum.conversoes import data_ddmmaaaa, sim_nao, so_digitos, titular_dependente


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
