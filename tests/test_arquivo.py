"""ArquivoDBK: leitura, busca, inserção e gravação."""

import os
import subprocess
import sys

import pytest

from conftest import DADOS, DBKS_DO_PROGRAMA, RAIZ
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.dbk.arquivo import tipo_da_linha


@pytest.mark.parametrize("dbk", DBKS_DO_PROGRAMA, ids=lambda p: p.stem)
def test_ler_e_gravar_sem_alterar_nada_devolve_o_mesmo_arquivo(dbk, tmp_path):
    saida = tmp_path / "copia.DBK"
    ArquivoDBK.ler(dbk).gravar(saida)
    assert saida.read_bytes() == dbk.read_bytes()


def test_tipos_e_cpf_do_arquivo_de_entrada():
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    tipos = [tipo_da_linha(linha) for linha in arquivo.linhas]

    assert tipos == ["IR", "16", "19", "20", "26", "27", "27", "27", "27", "37", "37", "37", "37", "T9"]
    assert arquivo.indices("27") == [5, 6, 7, 8]
    assert arquivo.cpf_declarante == "77039677008"


def test_nova_linha_entra_depois_da_ultima_do_mesmo_tipo():
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    assert arquivo.posicao_para("27") == 9


def test_dbk_do_programa_nao_tem_quebra_depois_da_ultima_linha():
    for dbk in DBKS_DO_PROGRAMA:
        assert not dbk.read_bytes().endswith(b"\r\n")
        assert ArquivoDBK.ler(dbk).quebra_no_fim is False


def sem_tipos(arquivo: ArquivoDBK, *tipos: str) -> ArquivoDBK:
    return ArquivoDBK([l for l in arquivo.linhas if tipo_da_linha(l) not in tipos], arquivo.quebra_no_fim)


def test_sem_bens_a_linha_27_entra_antes_da_37():
    arquivo = sem_tipos(ArquivoDBK.ler(DADOS / "entrada.DBK"), "27")
    posicao = arquivo.inserir("27", "27NOVA")
    assert [tipo_da_linha(l) for l in arquivo.linhas][posicao - 1:posicao + 2] == ["26", "27", "37"]


def test_sem_bens_nem_37_a_linha_27_entra_antes_do_rodape():
    arquivo = sem_tipos(ArquivoDBK.ler(DADOS / "entrada.DBK"), "27", "37")
    posicao = arquivo.inserir("27", "27NOVA")
    assert [tipo_da_linha(l) for l in arquivo.linhas][posicao:] == ["27", "T9"]


def test_main_com_dbk_sem_bens(tmp_path):
    """Antes da refatoração, um DBK sem nenhuma linha 27 quebrava o main (IndexError)."""
    entrada = tmp_path / "sem_bens.DBK"
    sem_tipos(ArquivoDBK.ler(DADOS / "entrada.DBK"), "27", "37").gravar(entrada)
    saida = tmp_path / "saida.DBK"
    ambiente = {**os.environ, "RAW_FILE": str(entrada), "OUTPUT_FILE": str(saida),
                "CLIENT_DATA": str(DADOS / "bens.json")}

    execucao = subprocess.run([sys.executable, "-m", "irpf_bot_2027.main"],
                              cwd=RAIZ, env=ambiente, capture_output=True, text=True)

    assert execucao.returncode == 0, execucao.stderr
    linhas = ArquivoDBK.ler(saida).linhas
    assert [tipo_da_linha(l) for l in linhas][-3:] == ["27", "27", "T9"]
    assert [l[891:896] for l in linhas if l.startswith("27")] == ["00001", "00002"]
