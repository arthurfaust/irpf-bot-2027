"""Testes das pendências resolvidas em 11/11/2026: CPF do JSON, controle do cabeçalho e negativos."""

import json
import os
import subprocess
import sys

import pytest

from conftest import DADOS, DBKS_DO_PROGRAMA, RAIZ, ler_linhas
from irpf_bot_2027.dbk import Campo
from irpf_bot_2027.leiautes.atual import controle_cabecalho
from irpf_bot_2027.main import conferir_cpf

CPF_DBK = "77039677008"     # CPF fictício dos DBKs de teste


# --- CPF do JSON x CPF do DBK ---

@pytest.mark.parametrize("cpf", ["77039677008", "770.396.770-08", 77039677008])
def test_cpf_igual_ao_do_dbk_e_aceito(cpf):
    assert conferir_cpf({"cpf": cpf}, CPF_DBK) is None


@pytest.mark.parametrize("dados, trecho", [
    ({}, 'não tem a chave "cpf"'),
    ({"cpf": "7703967700"}, "11 dígitos"),
    ({"cpf": "52998224725"}, "não é o CPF do declarante"),
])
def test_cpf_ausente_invalido_ou_de_outra_pessoa_e_recusado(dados, trecho):
    erro = conferir_cpf(dados, CPF_DBK)
    assert trecho in erro
    assert "52998224725" not in erro            # a mensagem não repete o CPF


def test_main_recusa_json_de_outro_cpf(tmp_path):
    dados = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))
    dados["cpf"] = "52998224725"
    json_outro = tmp_path / "outro_cpf.json"
    json_outro.write_text(json.dumps(dados), encoding="utf-8")
    saida = tmp_path / "saida.DBK"
    ambiente = {
        **os.environ,
        "RAW_FILE": str(DADOS / "entrada.DBK"),
        "OUTPUT_FILE": str(saida),
        "CLIENT_DATA": str(json_outro),
    }

    execucao = subprocess.run(
        [sys.executable, "-m", "irpf_bot_2027.main"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True,
    )

    assert execucao.returncode == 1
    assert "não é o CPF do declarante" in execucao.stderr
    assert "52998224725" not in execucao.stderr
    assert not saida.exists()


# --- Controle do cabeçalho IR ---

@pytest.mark.parametrize("dbk", DBKS_DO_PROGRAMA + [DADOS / "esperado.DBK"], ids=lambda p: p.stem)
def test_controle_do_cabecalho_usa_o_nome_do_arquivo(dbk):
    cabecalho = ler_linhas(dbk)[0]
    # Os DBKs foram gravados pelo programa com nome começando pelo CPF; só os 8 primeiros caracteres contam.
    assert controle_cabecalho(cabecalho, "77039677008-IRPF-A-2026-2025-ORIGI.DBK") == cabecalho[-10:]
    assert controle_cabecalho(cabecalho, "77039677.dbk") == cabecalho[-10:]
    assert controle_cabecalho(cabecalho, "entrada.DBK") != cabecalho[-10:]


# --- Valores negativos ---

def test_negativo_tem_o_sinal_na_primeira_posicao():
    """Formato do programa (CampoTXT.set(Valor) + getTxt): "-" seguido dos dígitos com zeros à esquerda."""
    campo = Campo(1, 13, "N", 2)
    assert campo.formatar("-123.45") == "-000000012345"
    assert campo.formatar("123.45") == "0000000012345"
