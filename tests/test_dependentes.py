"""Ficha Dependentes (registro 25, docs/adr/0024).

dependentes_programa.DBK foi gravado pelo programa IRPF 2026 em 18/11/2026 com os 4 dependentes de
dependentes.json, digitados nessa ordem (31, 21, 11, 22). O programa mantém a ordem e numera a chave
de 1 a 4. pagamentos_importados.DBK tem um dependente importado do IRPF 2025, sem o tipo.
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import dependentes
from irpf_bot_2027.fichas.dependentes.ficha import montar_linha, validar_item
from irpf_bot_2027.leiautes.irpf2026.registro25 import Registro25

CPF = "77039677008"
ITENS = json.loads((DADOS / "dependentes.json").read_text(encoding="utf-8"))["dependentes"]
LINHAS = [l for l in ler_linhas(DADOS / "dependentes_programa.DBK") if l.startswith("25")]
PAI, FILHO, CONJUGE, UNIVERSITARIO = ITENS
JOAO = {"tipo": "21", "nome": "Joao Teste", "cpf": "222.333.444-05", "data_nascimento": "2012-03-20"}


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "dependentes_programa.DBK")


def dbk_sem_dependentes() -> ArquivoDBK:
    arquivo = dbk_do_programa()
    arquivo.linhas = [l for l in arquivo.linhas if not l.startswith("25")]
    return arquivo


def gravar(arquivo, *itens):
    campos, erros = dependentes.validar(list(itens), CPF)
    assert erros == []
    return dependentes.inserir(arquivo, list(itens), campos)


# --- leiaute ---

@pytest.mark.parametrize(("item", "chave", "linha_do_programa"),
                         [(i, n, l) for n, (i, l) in enumerate(zip(ITENS, LINHAS, strict=True), start=1)],
                         ids=["pai", "filho_mora", "conjuge_contato", "universitario"])
def test_linha_igual_a_gravada_pelo_programa(item, chave, linha_do_programa):
    campos, erros = validar_item(item, CPF)
    assert erros == []
    assert montar_linha(campos, CPF, chave) == linha_do_programa


# --- validação ---

@pytest.mark.parametrize(("mudanca", "erro"), [
    ({"tipo": "12"}, "'tipo': esperado um dos códigos da ficha"),
    ({"tipo": None}, "campo obrigatório 'tipo' não informado"),
    ({"nome": ""}, "campo obrigatório 'nome' não informado"),
    ({"cpf": "777.888.999-42"}, "'cpf': CPF (11 dígitos) inválido"),
    ({"cpf": "770.396.770-08"}, "'cpf': o dependente não pode ser o próprio declarante"),
    ({"data_nascimento": "10/05/2015"}, "'data_nascimento': esperada data no formato \"AAAA-MM-DD\""),
    ({"data_nascimento": "2002-12-31"}, "'data_nascimento': o tipo 21 exige nascimento a partir de 01/01/2003"),
    ({"data_nascimento": "2026-01-01"}, "'data_nascimento': posterior ao ano-calendário 2025"),
    ({"mora_com_titular": "sim"}, "'mora_com_titular': esperado true ou false"),
    ({"email": "sem-arroba"}, "'email': formato inválido"),
    ({"ddd": "11"}, "'ddd' e 'celular': informe os dois, com 2 e 9 dígitos"),
    ({"ddd": "11", "celular": "1234-5678"}, "'ddd' e 'celular': informe os dois, com 2 e 9 dígitos"),
    ({"raca_cor": "azul"}, "'raca_cor': esperado um de"),
    ({"parentesco": "filho"}, "campo desconhecido 'parentesco'"),
])
def test_validacao(mudanca, erro):
    item = {k: v for k, v in {**FILHO, **mudanca}.items() if v is not None}
    _, erros = validar_item(item, CPF)
    assert len(erros) == 1 and erros[0].startswith(erro), erros


def test_limite_de_idade_do_universitario():
    _, erros = validar_item({**UNIVERSITARIO, "data_nascimento": "1999-12-31"}, CPF)
    assert erros == ["'data_nascimento': o tipo 22 exige nascimento a partir de 01/01/2000"]
    assert validar_item({**PAI, "data_nascimento": "1930-01-01"}, CPF)[1] == []     # 31 sem limite


def test_cpf_repetido_no_json():
    _, erros = dependentes.validar([FILHO, {**PAI, "cpf": FILHO["cpf"]}], CPF)
    assert erros == ["dependente 1: 'cpf': o mesmo CPF aparece em outro dependente do JSON",
                     "dependente 2: 'cpf': o mesmo CPF aparece em outro dependente do JSON"]


# --- inserção e busca ---

def test_insere_na_ordem_do_json_com_chave_sequencial():
    arquivo = dbk_sem_dependentes()
    resultado = gravar(arquivo, *ITENS)
    assert resultado.novos == [1, 2, 3, 4]
    assert arquivo.linhas == dbk_do_programa().linhas


def test_dependente_do_dbk_fica_e_campo_diferente_gera_aviso(caplog):
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, {**FILHO, "nome": "Outro Nome", "mora_com_titular": False})
    assert resultado.encontrados == [1] and resultado.diferentes == [1] and arquivo.linhas == antes
    assert "nome, mora_com_titular" in caplog.text
    assert resultado.dbk_nao_informados == [1, 3, 4]


def test_novo_recebe_a_proxima_chave():
    arquivo = dbk_do_programa()
    resultado = gravar(arquivo, JOAO)
    assert resultado.novos == [1]
    nova = arquivo.linhas_do_tipo("25")[-1]
    assert Registro25.CHAVE.ler(nova) == "00005"


def test_dependente_importado_recebe_o_tipo():
    """A importação traz o dependente sem o tipo (pendência "Tipo de dependente" no programa)."""
    arquivo = ArquivoDBK.ler(DADOS / "pagamentos_importados.DBK")
    (importado,) = arquivo.linhas_do_tipo("25")
    assert Registro25.CODIGO.ler(importado).strip() == ""
    resultado = gravar(arquivo, {**JOAO, "mora_com_titular": True})
    assert resultado.encontrados == [1] and resultado.diferentes == [1]      # mora: o DBK tem 0 (não)
    (atualizado,) = arquivo.linhas_do_tipo("25")
    assert Registro25.CODIGO.ler(atualizado) == "21"
    assert Registro25.CHAVE.ler(atualizado) == Registro25.CHAVE.ler(importado)
    assert Registro25.gravar_cod_controle(atualizado) == atualizado


def test_cpf_de_alimentando_vai_para_revisao():
    arquivo = ArquivoDBK.ler(DADOS / "pagamentos_importados.DBK")
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, {**JOAO, "cpf": "333.444.555-08"})
    assert resultado.revisao == [1] and arquivo.linhas == antes


def test_relatorio_sem_dados_do_cliente():
    resultado = gravar(dbk_do_programa(), {**FILHO, "nome": "Outro"}, JOAO)
    texto = "\n".join(t for _, t in dependentes.relatorio(resultado))
    assert "1 encontrado(s), 1 novo(s), 0 para revisão" in texto
    assert "itens da ficha): 1, 3, 4" in texto
    assert not any(d in texto for d in ("77788899941", "FILHO", "JOAO", "2015"))


# --- main: dependente novo e pagamento dele na mesma execução ---

def test_main_grava_dependente_e_pagamento_dele(tmp_path):
    from test_fichas_e_leiaute import rodar_main
    pagamento = {"codigo": "26", "tipo": "D", "cpf_dependente_alimentando": FILHO["cpf"],
                 "cnpj_cpf": "33.000.167/0001-01", "nome": "Operadora", "valor_pago": "100.00"}
    execucao, saida = rodar_main(tmp_path, {"cpf": CPF, "dependentes": [FILHO], "pagamentos": [pagamento]})
    assert execucao.returncode == 0, execucao.stderr
    assert "Dependentes: 0 encontrado(s), 1 novo(s)" in execucao.stderr
    assert "Pagamentos Efetuados: 0 preenchido(s), 1 novo(s), 0 para revisão" in execucao.stderr
    gravado = ArquivoDBK.ler(saida)
    assert gravado.linhas_do_tipo("25")[0][13:18] == "00001"
