"""Dígito verificador da conta (leiautes/irpf2026/dv_conta.py, transcrito do ValidadorDvContaCorrente).

CONTAS são as do roteiro manual tests/manual/dv_conta/ (teste1_validas). Confirmado no programa em
19/11/2026: a restauração do teste1 não teve nenhum aviso "DV da conta inválido"; a do teste2 (mesmas
contas com outro dígito) teve o aviso em todos os 16 bens.
"""

import logging

import pytest

from irpf_bot_2027.fichas import bens
from irpf_bot_2027.leiautes.irpf2026.dv_conta import dv_confere, modulo10, modulo11

# banco: (agência, conta como no DBK, DV que confere)
CONTAS = {
    "001": ("1234", "123456", "0"), "003": ("123", "123456", "0"), "004": ("123", "123456", "9"),
    "021": ("1234", "123456", "6"), "033": ("1234", "13001234", "2"), "037": ("1234", "123456", "0"),
    "041": ("1234", "350123456", "3"), "047": ("123", "1234567", "4"), "070": ("1234", "123456", "0"),
    "104": ("1234", "000012345678", "9"), "237": ("1234", "123456", "0"), "341": ("1234", "12345", "1"),
    "389": ("1234", "1234567", "8"), "422": ("123", "123456", "1"), "745": ("1234", "1234567", "9"),
    "756": ("1234", "1234567", "9"),
}


@pytest.mark.parametrize("banco", CONTAS)
def test_so_um_digito_confere(banco):
    agencia, conta, certo = CONTAS[banco]
    assert [d for d in "0123456789" if dv_confere(banco, agencia, conta, d)] == [certo]


def test_modulos():
    assert modulo11("98765") == 4            # 5*2 + 6*3 + 7*4 + 8*5 + 9*6 = 150; 150 % 11 = 7
    assert modulo10("12345") == 5            # 5*2=10->1, 4, 3*2=6, 2, 1*2=2: 15; 10 - 5


def test_banco_do_brasil_aceita_x_quando_o_resto_e_10():
    conta = next(c for c in map(str, range(10000, 20000)) if modulo11(c) == 10)
    assert dv_confere("001", "1234", conta, "X") and dv_confere("001", "1234", conta, "x")
    assert not dv_confere("001", "1234", conta, "0")


def test_bradesco_aceita_p_quando_o_resto_e_1():
    conta = next(c for c in map(str, range(100000, 200000))
                 if sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(c))) % 11 == 1)
    assert dv_confere("237", "1234", conta, "P") and dv_confere("237", "1234", conta, "0")


def test_caixa_usa_os_ultimos_9_digitos_da_conta():
    assert dv_confere("104", "1234", "000012345678", "9") == dv_confere("104", "9999", "999000012345678", "9")


@pytest.mark.parametrize(("banco", "conta", "dv", "esperado"), [
    ("341", "12345", "X", False),            # letra onde o cálculo espera número
    ("341", "12345", "12", False),           # DV com mais de um caractere
    ("341", "12345", "", True),              # sem DV: o programa não confere
    ("748", "12345", "7", True),             # Sicredi: sempre aceito
    ("260", "12345", "7", True),             # banco sem regra (Nubank)
])
def test_casos_especiais(banco, conta, dv, esperado):
    assert dv_confere(banco, "1234", conta, dv) is esperado


def test_bem_com_dv_errado_e_gravado_com_aviso(caplog):
    conta = {"grupo": "06", "codigo": "01", "pais": "105", "cnpj_cpf": "00.000.000/0001-91",
             "discriminacao": "Conta", "situacao_anterior": "0.00", "situacao_atual": "1.00",
             "pertence_a": {"tipo": "T"},
             "conta": {"banco": "001", "agencia": "1234", "conta": "98765", "dv": "X", "conta_pagamento": False}}
    with caplog.at_level(logging.WARNING):
        _, erros = bens.validar([conta, {**conta, "conta": {**conta["conta"], "dv": "4"}}])
    assert erros == []
    avisos = [r.getMessage() for r in caplog.records if "dígito verificador" in r.getMessage()]
    assert len(avisos) == 1 and avisos[0].startswith("Bem 1:") and "98765" not in avisos[0]
