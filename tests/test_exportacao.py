"""Exportação DBK -> JSON (docs/adr/0026).

Ida e volta: exportar um DBK gravado pelo programa, tirar dele os itens da ficha e lançar de novo o
que foi exportado reproduz as linhas do programa (nos bens, menos a chave e o controle, porque os
bens relançados recebem chaves novas).
"""

import json
import logging
import sys

import pytest

from conftest import DADOS
from irpf_bot_2027 import exportar as comando
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.exportar import exportar_dbk
from irpf_bot_2027.fichas import alimentandos, bens, dependentes, pagamentos, rendimentos_pj
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CPF = "77039677008"


def ida_e_volta(ficha, dbk: str, tipo: str, comparar=lambda l: l):
    original = ArquivoDBK.ler(DADOS / dbk)
    itens = ficha.exportar(original)
    assert itens and all("dbk" in item for item in itens)
    sem_referencia = [{k: v for k, v in item.items() if k != "dbk"} for item in itens]
    novo = ArquivoDBK([l for l in original.linhas if l[:2] != tipo], original.quebra_no_fim)
    campos, erros = ficha.validar(sem_referencia, CPF)
    assert erros == []
    ficha.inserir(novo, sem_referencia, campos)
    assert [comparar(l) for l in novo.linhas_do_tipo(tipo)] == [comparar(l) for l in original.linhas_do_tipo(tipo)]
    return itens


@pytest.mark.parametrize("dbk", ["contas_programa.DBK", "bolsa_programa.DBK", "veiculo_programa.DBK",
                                 "exterior_programa.DBK"])
def test_bens(dbk):
    ida_e_volta(bens, dbk, "27", comparar=lambda l: Registro27.CHAVE.gravar(l, 0)[:-10])


def test_rendimentos_pj():
    itens = ida_e_volta(rendimentos_pj, "rendpj_programa.DBK", "21")
    assert itens[0]["dbk"] == {"item": 1} and itens[0]["rendimentos"] == "85000.00"


def test_dependentes():
    itens = ida_e_volta(dependentes, "dependentes_programa.DBK", "25")
    assert [i["dbk"]["chave"] for i in itens] == [1, 2, 3, 4]
    assert itens[2]["raca_cor"] == "branca" and itens[2]["email"] == "conjuge@teste.com"


def test_alimentandos():
    itens = ida_e_volta(alimentandos, "alimentandos_programa.DBK", "35")
    assert "decisao_judicial" in itens[0] and "escritura_publica" in itens[1]
    assert set(itens[2]) >= {"decisao_judicial", "escritura_publica"}


def test_pagamentos():
    itens = ida_e_volta(pagamentos, "pagamentos_programa.DBK", "26")
    pensao = next(i for i in itens if i["codigo"] == "30")
    assert pensao["cpf_dependente_alimentando"] == "33344455508" and "nome" not in pensao


def test_declaracao_importada_sai_sem_os_campos_em_branco():
    dados = exportar_dbk(ArquivoDBK.ler(DADOS / "pagamentos_importados.DBK"))
    (dependente,) = dados["dependentes"]
    assert "tipo" not in dependente and dependente["dbk"] == {"chave": 1}
    (alimentanda,) = dados["alimentandos"]
    assert "data_nascimento" not in alimentanda and "decisao_judicial" not in alimentanda
    assert all(p["valor_pago"] == "0.00" for p in dados["pagamentos"])


def test_comando_grava_o_json_e_o_log_nao_tem_dados(tmp_path, monkeypatch, caplog):
    saida = tmp_path / "dbk.json"
    monkeypatch.setattr(sys, "argv", ["irpf-bot-2027-exportar", str(DADOS / "pagamentos_programa.DBK"), str(saida)])
    with caplog.at_level(logging.INFO):
        comando.main()
    dados = json.loads(saida.read_text(encoding="utf-8"))
    assert dados["cpf"] == CPF and len(dados["pagamentos"]) == 8 and len(dados["dependentes"]) == 1
    assert "Pagamentos Efetuados: 8 item(ns)" in caplog.text
    assert not any(d in caplog.text for d in (CPF, "MEDICO", "33344455508"))
