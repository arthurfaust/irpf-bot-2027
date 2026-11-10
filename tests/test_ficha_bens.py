"""Ficha de bens: validação da lista inteira, chaves e montagem da linha 27."""

import json

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.ficha import montar_linha, proxima_chave
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

BENS = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]


def test_validar_lista_valida():
    campos_por_bem, erros = bens.validar(BENS)
    assert erros == []
    assert len(campos_por_bem) == len(BENS)


def test_validar_numera_os_erros_pelo_bem():
    _, erros = bens.validar([BENS[0], {**BENS[1], "codigo": "05"}])
    assert erros == ["bem 2: grupo/código 01/05 não existe"]


def test_proxima_chave_continua_da_maior_existente():
    assert proxima_chave(ArquivoDBK.ler(DADOS / "entrada.DBK")) == 10


def test_montar_linha_reproduz_a_linha_da_referencia():
    """A linha do bitcoin montada isoladamente é igual à que está no DBK de referência."""
    campos_por_bem, _ = bens.validar(BENS)
    linha = montar_linha(BENS[0], campos_por_bem[0], "77039677008", 10)

    referencia = ArquivoDBK.ler(DADOS / "esperado.DBK").linhas_do_tipo(Registro27.TIPO)
    assert linha in referencia


def test_inserir_coloca_os_bens_em_ordem_com_chaves_seguidas():
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    campos_por_bem, _ = bens.validar(BENS)

    bens.inserir(arquivo, BENS, campos_por_bem)

    novas = arquivo.linhas_do_tipo(Registro27.TIPO)[-2:]
    assert [Registro27.CHAVE.ler(l) for l in novas] == ["00010", "00011"]
    assert [Registro27.GRUPO.ler(l) + Registro27.CODIGO.ler(l) for l in novas] == ["0801", "0111"]
