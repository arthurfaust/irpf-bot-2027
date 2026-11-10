"""Rede de segurança da refatoração.

Roda o main.py com uma entrada fixa e compara a saída, byte a byte, com o DBK de referência
(tests/dados/esperado.DBK). Essa referência foi gerada pelo código em 09/11/2026 e importada com
sucesso no IRPF 2026. Se o teste falhar, o comportamento do bot mudou.
"""

import os
import subprocess
import sys

from conftest import DADOS, RAIZ


def test_saida_igual_a_referencia(tmp_path):
    saida = tmp_path / "saida.DBK"
    ambiente = {
        **os.environ,
        "RAW_FILE": str(DADOS / "entrada.DBK"),
        "OUTPUT_FILE": str(saida),
        "CLIENT_DATA": str(DADOS / "bens.json"),
    }

    execucao = subprocess.run(
        [sys.executable, "-m", "irpf_bot_2027.main"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True,
    )

    assert execucao.returncode == 0, execucao.stderr
    assert saida.read_bytes() == (DADOS / "esperado.DBK").read_bytes()


def test_json_invalido_nao_grava_nada(tmp_path):
    json_invalido = tmp_path / "invalido.json"
    json_invalido.write_text(
        '{"bens": [{"grupo": "07", "codigo": "05", "pais": "105", "discriminacao": "x",'
        ' "situacao_anterior": "1", "situacao_atual": "1"}]}',
        encoding="utf-8",
    )
    saida = tmp_path / "saida.DBK"
    ambiente = {
        **os.environ,
        "RAW_FILE": str(DADOS / "entrada.DBK"),
        "OUTPUT_FILE": str(saida),
        "CLIENT_DATA": str(json_invalido),
    }

    execucao = subprocess.run(
        [sys.executable, "-m", "irpf_bot_2027.main"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True,
    )

    assert execucao.returncode == 1
    assert not saida.exists()


def test_dbk_de_outro_exercicio_e_recusado(tmp_path):
    """Um DBK de 2027 (ou de 2025) não pode ser gravado com as posições do leiaute de 2026."""
    original = (DADOS / "entrada.DBK").read_bytes()
    assert original[8:16] == b"20262025"
    entrada = tmp_path / "outro_ano.DBK"
    entrada.write_bytes(original[:8] + b"20272026" + original[16:])
    saida = tmp_path / "saida.DBK"
    ambiente = {
        **os.environ,
        "RAW_FILE": str(entrada),
        "OUTPUT_FILE": str(saida),
        "CLIENT_DATA": str(DADOS / "bens.json"),
    }

    execucao = subprocess.run(
        [sys.executable, "-m", "irpf_bot_2027.main"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True,
    )

    assert execucao.returncode == 1
    assert "exercício 2027" in execucao.stderr
    assert not saida.exists()
