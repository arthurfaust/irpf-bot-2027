"""Confere as posições do Registro27 contra linhas 27 gravadas pelo próprio programa."""

import zlib
from decimal import Decimal

import pytest

from conftest import linhas_27
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CAMPOS = list(Registro27.campos().values())
LINHAS = linhas_27()


def test_campos_cobrem_a_linha_inteira_sem_buracos():
    posicao = 1
    for campo in CAMPOS:
        assert campo.ini == posicao, f"buraco ou sobreposição antes da posição {campo.ini}"
        posicao = campo.fim + 1
    assert posicao - 1 == Registro27.TAMANHO


@pytest.mark.parametrize("linha", [l for _, l in LINHAS], ids=[i for i, _ in LINHAS])
def test_linha_do_programa_tem_tamanho_e_controle_certos(linha):
    assert len(linha) == Registro27.TAMANHO
    assert Registro27.gravar_cod_controle(linha) == linha


@pytest.mark.parametrize("linha", [l for _, l in LINHAS], ids=[i for i, _ in LINHAS])
def test_ida_e_volta(linha):
    """Ler cada campo como valor e formatar de novo tem que devolver exatamente o texto original."""
    for campo in CAMPOS:
        bruto = campo.ler(linha)
        if campo.tipo == "N":
            valor = Decimal(bruto) / 10 ** campo.decimais if campo.decimais else int(bruto)
        else:
            valor = bruto.rstrip()
        assert campo.formatar(valor) == bruto, f"campo {campo.ini}-{campo.fim}"


def test_controle_e_crc32_das_posicoes_1_a_1241():
    _, linha = LINHAS[0]
    assert int(Registro27.CONTROLE.ler(linha)) == zlib.crc32(linha[:1241].encode("latin-1"))


@pytest.mark.parametrize("linha", [l for _, l in LINHAS], ids=[i for i, _ in LINHAS])
def test_ler_tudo_devolve_todos_os_campos_e_reconstroi_a_linha(linha):
    lido = Registro27.ler_tudo(linha)
    assert list(lido) == list(Registro27.campos())
    assert len(lido["GRUPO"]) == 2 and len(lido["CODIGO"]) == 2      # zeros à esquerda preservados
    for nome, campo in Registro27.campos().items():
        if campo.tipo == "N":
            assert lido[nome] == campo.ler(linha), nome
        else:
            assert not lido[nome].endswith(" "), nome
            assert campo.gravar(linha, lido[nome]) == linha, nome      # gravar o texto lido não muda a linha


@pytest.mark.parametrize("linha_errada", ["27" + " " * 10, "26" + " " * (Registro27.TAMANHO - 2)])
def test_ler_tudo_recusa_linha_de_outro_tipo_ou_tamanho(linha_errada):
    with pytest.raises(ValueError, match="registro 27"):
        Registro27.ler_tudo(linha_errada)
