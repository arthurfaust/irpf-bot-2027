"""Fase 3: procurar o fundo nacional no DBK pelo CNPJ e atualizar (1), lançar (0) ou revisar (2+)."""

import json
import logging
from decimal import Decimal

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, procurar
from irpf_bot_2027.fichas.bens.ficha import bem_do_dbk, montar_linha, proxima_chave
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CNPJ = "11222333000181"
FUNDO = {"grupo": "07", "codigo": "03", "pais": "105", "cnpj_cpf": "11.222.333/0001-81",
         "discriminacao": "Fundo imobiliario de teste", "situacao_anterior": "1000.00", "situacao_atual": "1500.00"}


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def feitos(resultado):
    """O que aconteceu com os bens do JSON."""
    return {"atualizados": resultado.atualizados, "novos": resultado.novos, "revisao": resultado.revisao}


def dbk_com_fundo(vezes=1):
    """entrada.DBK com o FUNDO já lançado (como se viesse da declaração anterior)."""
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    [campos] = validados(FUNDO)
    for _ in range(vezes):
        linha = montar_linha(FUNDO, campos, arquivo.cpf_declarante, proxima_chave(arquivo))
        arquivo.inserir(Registro27.TIPO, linha)
    return arquivo


def linhas_do_fundo(arquivo):
    return [arquivo.linhas[i] for i in procurar(arquivo, ("07", CNPJ))]


# --- chave ---

def test_chave_do_fundo_nacional_e_grupo_mais_cnpj_so_digitos():
    assert chave_busca(validados(FUNDO)[0]) == ("07", CNPJ)


@pytest.mark.parametrize("bem", [
    {**FUNDO, "codigo": "99", "pais": "249", "cnpj_cpf": None},          # fundo no exterior
    {"grupo": "01", "codigo": "11", "pais": "105", "discriminacao": "Apto",
     "situacao_anterior": "0.00", "situacao_atual": "1.00"},               # imóvel: ainda sem busca
], ids=["fundo_exterior", "imovel"])
def test_tipos_sem_busca_nao_tem_chave(bem):
    bem = {k: v for k, v in bem.items() if v is not None}
    campos, _ = bens.validar([bem])
    assert chave_busca(campos[0]) is None


# --- 0 encontrados ---

def test_fundo_que_nao_esta_no_dbk_e_lancado_completo():
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    total = len(arquivo.linhas_do_tipo("27"))

    resultado = gravar(arquivo, FUNDO)

    assert feitos(resultado) == {"atualizados": [], "novos": [1], "revisao": []}
    assert len(arquivo.linhas_do_tipo("27")) == total + 1
    [linha] = linhas_do_fundo(arquivo)
    assert Registro27.VALOR_ANTERIOR.ler(linha) == "0000000100000"


# --- 1 encontrado ---

def test_fundo_que_esta_no_dbk_tem_so_a_situacao_atual_atualizada():
    arquivo = dbk_com_fundo()
    [antes] = linhas_do_fundo(arquivo)
    total = len(arquivo.linhas)
    novo = {**FUNDO, "codigo": "03", "situacao_anterior": "1000.00", "situacao_atual": "2345.67",
            "discriminacao": "Outra descricao"}

    resultado = gravar(arquivo, novo)

    assert feitos(resultado) == {"atualizados": [1], "novos": [], "revisao": []}
    assert len(arquivo.linhas) == total                                    # nada inserido
    [depois] = linhas_do_fundo(arquivo)
    assert Registro27.VALOR_ATUAL.ler(depois) == "0000000234567"
    # Só a situação atual e o controle mudam; discriminação e chave ficam as do DBK.
    diferencas = {nome for nome, campo in Registro27.campos().items() if campo.ler(antes) != campo.ler(depois)}
    assert diferencas == {"VALOR_ATUAL", "CONTROLE"}
    assert Registro27.gravar_cod_controle(depois) == depois


def test_situacao_anterior_do_dbk_nunca_e_alterada(caplog):
    arquivo = dbk_com_fundo()
    divergente = {**FUNDO, "situacao_anterior": "9999.99"}

    gravar(arquivo, divergente)

    [linha] = linhas_do_fundo(arquivo)
    assert Registro27.VALOR_ANTERIOR.ler(linha) == "0000000100000"
    assert "situação anterior do JSON difere da do DBK" in caplog.text
    assert "9999" not in caplog.text                                       # sem valores do cliente no log


# --- 2 ou mais ---

def test_fundo_repetido_no_dbk_nao_e_gravado_e_vai_para_revisao(caplog):
    arquivo = dbk_com_fundo(vezes=2)
    antes = list(arquivo.linhas)

    resultado = gravar(arquivo, {**FUNDO, "situacao_atual": "1.00"})

    assert feitos(resultado) == {"atualizados": [], "novos": [], "revisao": [1]}
    assert arquivo.linhas == antes
    assert "2 lançamentos no DBK com a mesma chave" in caplog.text


def test_dois_bens_do_json_para_o_mesmo_lancamento_vao_para_revisao():
    arquivo = dbk_com_fundo()
    antes = list(arquivo.linhas)

    resultado = gravar(arquivo, {**FUNDO, "situacao_atual": "1.00"}, {**FUNDO, "situacao_atual": "2.00"})

    assert feitos(resultado) == {"atualizados": [], "novos": [], "revisao": [1, 2]}
    assert arquivo.linhas == antes


def test_mistura_de_resultados_na_ordem_do_json():
    arquivo = dbk_com_fundo()
    outro_fundo = {**FUNDO, "cnpj_cpf": "11444777000161"}
    bitcoin = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"][0]     # sem busca

    resultado = gravar(arquivo, outro_fundo, {**FUNDO, "situacao_atual": "1.00"}, bitcoin)

    assert feitos(resultado) == {"atualizados": [2], "novos": [1, 3], "revisao": []}
    assert Decimal(Registro27.VALOR_ATUAL.ler(linhas_do_fundo(arquivo)[0])) == 100


# --- bens do DBK sem atualização e relatório ---

def chaves_nao_informadas(resultado):
    return [(b.chave, b.grupo, b.codigo, b.com_busca) for b in resultado.nao_informados]


def test_bens_do_dbk_nao_atualizados_vao_para_revisao_sem_mudar_nada():
    arquivo = dbk_com_fundo()                       # bens 1-9 da entrada + fundo com chave 10
    originais = list(arquivo.linhas)

    resultado = gravar(arquivo, {**FUNDO, "cnpj_cpf": "11444777000161"})     # outro fundo: novo

    assert chaves_nao_informadas(resultado) == [
        (b.chave, b.grupo, b.codigo, b.com_busca) for b in map(bem_do_dbk, ArquivoDBK.ler(DADOS / "entrada.DBK").linhas_do_tipo("27"))
    ] + [(10, "07", "03", True)]
    assert all(l in arquivo.linhas for l in originais)                       # nada zerado nem apagado


def test_bem_atualizado_nao_aparece_entre_os_nao_informados():
    arquivo = dbk_com_fundo()

    resultado = gravar(arquivo, {**FUNDO, "situacao_atual": "1.00"})

    assert 10 not in [b.chave for b in resultado.nao_informados]
    assert len(resultado.nao_informados) == len(arquivo.linhas_do_tipo("27")) - 1


def test_relatorio_resume_e_nao_tem_dados_do_cliente():
    arquivo = dbk_com_fundo(vezes=2)
    bitcoin = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"][0]

    resultado = gravar(arquivo, {**FUNDO, "situacao_atual": "1.00"}, bitcoin)
    texto = "\n".join(t for _, t in bens.relatorio(resultado))

    assert "0 atualizado(s), 1 novo(s), 1 para revisão" in texto
    assert "REVISÃO, não gravados (bens do JSON): 1" in texto
    assert "07/03" in texto and "tipo sem busca automática" in texto
    for dado in (CNPJ, "Fundo imobiliario", "1500", "11.222.333"):
        assert dado not in texto
    niveis = {nivel for nivel, t in bens.relatorio(resultado) if "REVISÃO" in t}
    assert niveis == {logging.WARNING}
