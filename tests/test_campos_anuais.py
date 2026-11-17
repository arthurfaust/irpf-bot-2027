"""Atualização de bem encontrado no DBK: discriminação e demais campos (docs/adr/0016).

Usa os DBKs gravados pelo programa (contas_programa.DBK e bolsa_programa.DBK) como declaração anterior.
"""

import json
import logging

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CONTAS = json.loads((DADOS / "contas.json").read_text(encoding="utf-8"))["bens"]
BOLSA = json.loads((DADOS / "bolsa.json").read_text(encoding="utf-8"))["bens"]
BB, CAIXA_POUPANCA = CONTAS[0], CONTAS[1]
PETR4 = BOLSA[0]
NOVA = "TEXTO NOVO DA DISCRIMINACAO"


def dbk(nome: str) -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / nome)


def linha_de(arquivo: ArquivoDBK, discriminacao: str) -> str:
    [linha] = [l for l in arquivo.linhas_do_tipo(Registro27.TIPO)
               if Registro27.DISCRIMINACAO.ler(l).rstrip() == discriminacao]
    return linha


def linha_pela_chave(arquivo: ArquivoDBK, chave: str) -> str:
    [linha] = [l for l in arquivo.linhas_do_tipo(Registro27.TIPO) if Registro27.CHAVE.ler(l) == chave]
    return linha


def alterar(arquivo: ArquivoDBK, discriminacao: str, **campos) -> str:
    """Muda campos da linha do DBK e devolve a CHAVE dela."""
    posicao = arquivo.linhas.index(linha_de(arquivo, discriminacao))
    linha = arquivo.linhas[posicao]
    for nome, valor in campos.items():
        linha = getattr(Registro27, nome).gravar(linha, valor)
    arquivo.substituir(posicao, Registro27.gravar_cod_controle(linha))
    return Registro27.CHAVE.ler(linha)


def gravar(arquivo, *lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return bens.inserir(arquivo, list(lista), campos)


def mudancas(antes: str, depois: str) -> set[str]:
    return {n for n, c in Registro27.campos().items() if c.ler(antes) != c.ler(depois)} - {"CONTROLE"}


# --- discriminação ---

def test_discriminacao_da_acao_e_substituida_pela_do_json(caplog):
    arquivo = dbk("bolsa_programa.DBK")
    chave = Registro27.CHAVE.ler(linha_de(arquivo, PETR4["discriminacao"]))
    with caplog.at_level(logging.INFO):
        resultado = gravar(arquivo, {**PETR4, "discriminacao": NOVA})
    assert resultado.atualizados == [1] and resultado.conferir == []
    assert Registro27.DISCRIMINACAO.ler(linha_pela_chave(arquivo, chave)).rstrip() == NOVA
    assert "discriminação substituída pela do JSON" in caplog.text


def test_discriminacao_da_conta_fica_a_do_dbk_e_gera_aviso(caplog):
    arquivo = dbk("contas_programa.DBK")
    antes = linha_de(arquivo, BB["discriminacao"])
    resultado = gravar(arquivo, {**BB, "discriminacao": NOVA})
    depois = linha_pela_chave(arquivo, Registro27.CHAVE.ler(antes))
    assert mudancas(antes, depois) == set()                      # mesma situação atual: nada muda
    assert resultado.conferir == [1]
    assert "diferente do DBK, mantido o do DBK: discriminacao" in caplog.text
    assert NOVA not in caplog.text                                # o log não repete o texto


def test_discriminacao_igual_com_outra_caixa_e_espacos_nao_gera_aviso():
    resultado = gravar(dbk("contas_programa.DBK"), {**BB, "discriminacao": "conta   corrente bb"})
    assert resultado.conferir == []


# --- demais campos ---

def test_campo_em_branco_no_dbk_recebe_o_do_json(caplog):
    arquivo = dbk("contas_programa.DBK")
    chave = alterar(arquivo, BB["discriminacao"], DV_CONTA="", CNPJ_CPF="")
    with caplog.at_level(logging.INFO):
        resultado = gravar(arquivo, BB)
    linha = linha_pela_chave(arquivo, chave)
    assert Registro27.DV_CONTA.ler(linha).strip() == "X"
    assert Registro27.CNPJ_CPF.ler(linha).strip() == "00000000000191"
    assert resultado.conferir == []
    assert "preenchidos (estavam em branco no DBK): cnpj_cpf, conta.dv" in caplog.text
    assert Registro27.gravar_cod_controle(linha) == linha


def test_campo_preenchido_e_diferente_fica_o_do_dbk(caplog):
    arquivo = dbk("contas_programa.DBK")
    antes = linha_de(arquivo, BB["discriminacao"])
    resultado = gravar(arquivo, {**BB, "situacao_atual": "1500.00", "conta": {**BB["conta"], "dv": "7"},
                                 "cnpj_cpf": "60.701.190/0001-04"})
    assert mudancas(antes, linha_pela_chave(arquivo, Registro27.CHAVE.ler(antes))) == set()
    assert resultado.conferir == [1]
    assert "mantido o do DBK: cnpj_cpf, conta.dv" in caplog.text
    assert "7" not in caplog.text.split("mantido o do DBK:")[1].split("\n")[0].replace("conta.dv", "")


def test_mesmo_valor_em_outro_formato_nao_gera_aviso():
    """A conta da Caixa no DBK tem zeros à esquerda; a agência veio sem zeros no JSON."""
    poupanca = {**CAIXA_POUPANCA, "conta": {**CAIXA_POUPANCA["conta"], "agencia": "0567"}}
    resultado = gravar(dbk("contas_programa.DBK"), poupanca)
    assert resultado.atualizados == [1] and resultado.conferir == []


def test_indicador_nao_e_campo_vazio():
    """USUFRUTO 0 no DBK é a resposta "Não": o "Sim" do JSON gera aviso, não preenche."""
    arquivo = dbk("contas_programa.DBK")
    antes = linha_de(arquivo, BB["discriminacao"])
    resultado = gravar(arquivo, {**BB, "usufruto": True})
    assert Registro27.USUFRUTO.ler(linha_pela_chave(arquivo, Registro27.CHAVE.ler(antes))) == "0"
    assert resultado.conferir == [1]


def test_situacao_anterior_diferente_tambem_entra_em_conferir():
    resultado = gravar(dbk("contas_programa.DBK"), {**BB, "situacao_anterior": "1.00"})
    assert resultado.conferir == [1]


def test_relatorio_lista_os_bens_a_conferir():
    resultado = gravar(dbk("contas_programa.DBK"), {**BB, "discriminacao": NOVA})
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "CONFERIR, atualizados com campo diferente do DBK" in texto
    assert NOVA not in texto
