"""País do bem: código, tabela do programa e restrições Brasil/exterior."""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.paises import BRASIL, PAISES, nome_pais, pais_existe

BITCOIN, APARTAMENTO = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]

FUNDO_EXTERIOR = {"grupo": "07", "codigo": "99", "pais": "111", "discriminacao": "Fundo X",
                  "situacao_anterior": "1000.00", "situacao_atual": "2000.00"}
POUPANCA = {"grupo": "04", "codigo": "01", "pais": "105", "discriminacao": "Poupança",
            "situacao_anterior": "0.00", "situacao_atual": "100.00"}


def test_tabela_de_paises():
    assert len(PAISES) == 248
    assert BRASIL == "105" and nome_pais("105") == "Brasil"
    assert nome_pais("111") == "Bulgária, República da"
    assert not pais_existe("999")


@pytest.mark.parametrize(("entrada", "esperado"), [("105", "105"), (105, "105"), ("13", "013"), (" 111 ", "111")])
def test_codigo_do_pais_e_normalizado(entrada, esperado):
    campos, erros = validar_bem({**BITCOIN, "pais": entrada})
    assert campos["PAIS"] == esperado
    assert not any("país" in erro for erro in erros), erros


@pytest.mark.parametrize("entrada", ["Brasil", "1050", "-105", True])
def test_codigo_do_pais_em_formato_errado(entrada):
    _, erros = validar_bem({**BITCOIN, "pais": entrada})
    assert "'pais': esperado o código do país com até 3 dígitos (ex.: \"105\" para o Brasil)" in erros


def test_pais_inexistente_e_barrado():
    _, erros = validar_bem({**BITCOIN, "pais": "999"})
    assert erros == ["país 999 não existe na tabela do programa"]


def test_fundo_no_exterior_e_aceito_fora_do_brasil():
    _, erros = validar_bem(FUNDO_EXTERIOR)
    assert erros == []


def test_fundo_no_exterior_e_barrado_no_brasil():
    _, erros = validar_bem({**FUNDO_EXTERIOR, "pais": "105"})
    assert erros == ["07/99 (Fundos de Investimento no Exterior - Lei 14.754/2023, arts. 2º a 14) "
                     "só pode estar localizado no exterior; veio 105 (Brasil)"]


def test_poupanca_e_barrada_no_exterior():
    _, erros = validar_bem({**POUPANCA, "pais": "111"})
    assert erros == ["04/01 (Depósito em conta poupança) só pode estar localizado no Brasil (país 105); "
                     "veio 111 (Bulgária, República da)"]


@pytest.mark.parametrize(("grupo", "codigo"), [("04", "03"), ("04", "04"), ("06", "02"), ("07", "01"), ("07", "13")])
def test_outros_codigos_somente_brasil(grupo, codigo):
    _, erros = validar_bem({**POUPANCA, "grupo": grupo, "codigo": codigo, "pais": "111"})
    assert any("só pode estar localizado no Brasil" in erro for erro in erros), erros


def test_bem_sem_restricao_aceita_brasil_e_exterior():
    for pais in ("105", "111"):
        _, erros = validar_bem({**BITCOIN, "pais": pais, "cripto": {"autocustodiante": True}})
        assert erros == [], (pais, erros)
