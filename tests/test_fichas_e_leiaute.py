"""Registro de fichas, leiaute em uso e comportamento do main com JSONs incomuns."""

import json
import os
import subprocess
import sys

import pytest

from conftest import DADOS, RAIZ
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import FICHAS
from irpf_bot_2027.leiautes import atual, irpf2026
from irpf_bot_2027.leiautes.irpf2026.cabecalho import verificar_exercicio


@pytest.mark.parametrize("ficha", FICHAS, ids=lambda f: f.CHAVE_JSON)
def test_toda_ficha_tem_a_forma_combinada(ficha):
    assert isinstance(ficha.NOME, str) and ficha.NOME
    assert isinstance(ficha.CHAVE_JSON, str) and ficha.CHAVE_JSON
    assert callable(ficha.validar)
    assert callable(ficha.inserir)


def test_chaves_json_das_fichas_nao_se_repetem():
    chaves = [ficha.CHAVE_JSON for ficha in FICHAS]
    assert len(chaves) == len(set(chaves))


def test_leiaute_em_uso_e_o_de_2026():
    assert (atual.EXERCICIO, atual.ANO_CALENDARIO) == (irpf2026.EXERCICIO, irpf2026.ANO_CALENDARIO) == ("2026", "2025")


def test_verificar_exercicio_aceita_dbk_de_2026():
    assert verificar_exercicio(ArquivoDBK.ler(DADOS / "entrada.DBK")) is None


def test_verificar_exercicio_recusa_dbk_sem_cabecalho():
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    sem_cabecalho = ArquivoDBK([l for l in arquivo.linhas if not l.startswith("IR")])
    assert "cabeçalho" in verificar_exercicio(sem_cabecalho)


def rodar_main(tmp_path, json_cliente: dict) -> tuple[subprocess.CompletedProcess, object]:
    arquivo_json = tmp_path / "cliente.json"
    arquivo_json.write_text(json.dumps(json_cliente), encoding="utf-8")
    saida = tmp_path / "saida.DBK"
    ambiente = {**os.environ, "RAW_FILE": str(DADOS / "entrada.DBK"), "OUTPUT_FILE": str(saida),
                "CLIENT_DATA": str(arquivo_json)}
    execucao = subprocess.run([sys.executable, "-m", "irpf_bot_2027.main"],
                              cwd=RAIZ, env=ambiente, capture_output=True, text=True)
    return execucao, saida


def test_chave_desconhecida_no_json_gera_aviso(tmp_path):
    bens = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))
    execucao, saida = rodar_main(tmp_path, {**bens, "rendimentos": []})

    assert execucao.returncode == 0, execucao.stderr
    assert "A chave 'rendimentos' do JSON não é de nenhuma ficha" in execucao.stderr
    assert saida.read_bytes() == (DADOS / "esperado.DBK").read_bytes()


def test_json_sem_itens_grava_o_dbk_sem_alteracoes(tmp_path):
    execucao, saida = rodar_main(tmp_path, {"cpf": "77039677008"})

    assert execucao.returncode == 0, execucao.stderr
    assert "não tem itens de nenhuma ficha" in execucao.stderr
    assert saida.read_bytes() == (DADOS / "entrada.DBK").read_bytes()


def test_erro_de_validacao_mostra_a_ficha(tmp_path):
    bens = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]
    execucao, saida = rodar_main(tmp_path, {"bens": [bens[0], {**bens[1], "codigo": "05"}]})

    assert execucao.returncode == 1
    assert "Bens e Direitos > bem 2: grupo/código 01/05 não existe" in execucao.stderr
    assert not saida.exists()
