"""Bloco veiculo: Renavam (02/01), registro de aeronave (02/02) e de embarcação (02/03).

veiculo_programa.DBK foi gravado pelo programa IRPF 2026 em 16/11/2026 com os mesmos 5 bens de
veiculo.json, digitados na tela (CPF fictício).
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.fichas.bens.ficha import montar_linha
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27
from irpf_bot_2027.leiautes.irpf2026.regras import renavam_valido

CPF = "77039677008"
BENS = json.loads((DADOS / "veiculo.json").read_text(encoding="utf-8"))["bens"]
LINHAS = [linha for linha in ler_linhas(DADOS / "veiculo_programa.DBK") if linha.startswith("27")]
CARRO, MOTO, CARRO_EXTERIOR, AERONAVE, LANCHA = BENS


def com_veiculo(bem: dict, **veiculo) -> dict:
    novo = {k: v for k, v in bem.items() if k != "veiculo"}
    return {**novo, "veiculo": veiculo} if veiculo else novo


@pytest.mark.parametrize(("bem", "linha_do_programa"), list(zip(BENS, LINHAS, strict=True)),
                         ids=[bem["discriminacao"] for bem in BENS])
def test_linha_igual_a_gravada_pelo_programa(bem, linha_do_programa):
    campos, erros = validar_bem(bem)
    assert erros == []
    assert montar_linha(bem, campos, CPF, int(Registro27.CHAVE.ler(linha_do_programa))) == linha_do_programa


@pytest.mark.parametrize(("bem", "gravado"), [(CARRO, "12345678900"), (MOTO, "00987654322"),
                                              (CARRO_EXTERIOR, "0ABC1234-FL")],
                         ids=["11_digitos", "9_digitos", "exterior"])
def test_registro_do_veiculo_ganha_zeros_ate_11(bem, gravado):
    campos, _ = validar_bem(bem)
    assert campos["RENAVAM"] == gravado


@pytest.mark.parametrize("renavam", ["12345678900", "987654322", "00987654322", "00639456170"])
def test_renavam_valido(renavam):
    assert renavam_valido(renavam)


@pytest.mark.parametrize("renavam", ["12345678901", "1234567890A", "123456789000", "", "987654321"])
def test_renavam_invalido(renavam):
    assert not renavam_valido(renavam)


@pytest.mark.parametrize("renavam", ["12345678901", "123.456.789-00", "1234567890123"])
def test_renavam_invalido_no_brasil_e_barrado(renavam):
    _, erros = validar_bem(com_veiculo(CARRO, renavam=renavam))
    assert erros == ["'veiculo.renavam': Renavam inválido; esperado 9 ou 11 dígitos, só números, "
                     "com o dígito verificador correto"]
    assert renavam not in erros[0]


def test_registro_no_exterior_nao_passa_pelo_renavam():
    _, erros = validar_bem(com_veiculo(CARRO_EXTERIOR, renavam="XYZ-9"))
    assert erros == []


@pytest.mark.parametrize(("bem", "chave", "codigo"), [(CARRO, "renavam", "01"),
                                                      (AERONAVE, "registro_aeronave", "02"),
                                                      (LANCHA, "registro_embarcacao", "03")],
                         ids=["veiculo", "aeronave", "embarcacao"])
def test_registro_e_obrigatorio_no_brasil(bem, chave, codigo):
    _, erros = validar_bem(com_veiculo(bem))
    assert len(erros) == 1
    assert erros[0].startswith(f"'veiculo.{chave}' é obrigatório para 02/{codigo} ")


def test_registro_do_veiculo_e_opcional_no_exterior():
    _, erros = validar_bem(com_veiculo(CARRO_EXTERIOR))
    assert erros == []


def test_registro_de_outro_tipo_nao_se_aplica():
    _, erros = validar_bem(com_veiculo(CARRO, renavam="12345678900", registro_aeronave="PT-ABC"))
    assert erros == ["'veiculo.registro_aeronave' não se aplica a 02/01 (Veículo automotor terrestre: "
                     "caminhão, automóvel, moto etc) no Brasil"]


def test_registro_com_mais_de_30_caracteres():
    _, erros = validar_bem(com_veiculo(LANCHA, registro_embarcacao="X" * 31))
    assert erros == ["'veiculo.registro_embarcacao': tem 31 caracteres; o máximo é 30"]
