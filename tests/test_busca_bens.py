"""Fase 3: procurar o fundo nacional no DBK pelo CNPJ e atualizar (1), lançar (0) ou revisar (2+)."""

import json
from decimal import Decimal

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, procurar
from irpf_bot_2027.fichas.bens.ficha import montar_linha, proxima_chave
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

    assert resultado == {"atualizados": [], "novos": [1], "revisao": []}
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

    assert resultado == {"atualizados": [1], "novos": [], "revisao": []}
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

    assert resultado == {"atualizados": [], "novos": [], "revisao": [1]}
    assert arquivo.linhas == antes
    assert "2 lançamentos no DBK com a mesma chave" in caplog.text


def test_dois_bens_do_json_para_o_mesmo_lancamento_vao_para_revisao():
    arquivo = dbk_com_fundo()
    antes = list(arquivo.linhas)

    resultado = gravar(arquivo, {**FUNDO, "situacao_atual": "1.00"}, {**FUNDO, "situacao_atual": "2.00"})

    assert resultado == {"atualizados": [], "novos": [], "revisao": [1, 2]}
    assert arquivo.linhas == antes


def test_mistura_de_resultados_na_ordem_do_json():
    arquivo = dbk_com_fundo()
    outro_fundo = {**FUNDO, "cnpj_cpf": "11444777000161"}
    bitcoin = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"][0]     # sem busca

    resultado = gravar(arquivo, outro_fundo, {**FUNDO, "situacao_atual": "1.00"}, bitcoin)

    assert resultado == {"atualizados": [2], "novos": [1, 3], "revisao": []}
    assert Decimal(Registro27.VALOR_ATUAL.ler(linhas_do_fundo(arquivo)[0])) == 100
