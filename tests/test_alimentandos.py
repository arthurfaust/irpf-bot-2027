"""Ficha Alimentandos (registro 35, docs/adr/0025).

alimentandos_programa.DBK foi gravado pelo programa IRPF 2026 em 18/11/2026 com os 3 alimentandos de
alimentandos.json (decisão judicial, escritura pública e os dois). pagamentos_importados.DBK tem uma
alimentanda importada do IRPF 2025, sem data de nascimento e sem tipo de processo.
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import alimentandos
from irpf_bot_2027.fichas.alimentandos.ficha import montar_linha, validar_item
from irpf_bot_2027.leiautes.irpf2026.registro35 import Registro35

CPF = "77039677008"
ITENS = json.loads((DADOS / "alimentandos.json").read_text(encoding="utf-8"))["alimentandos"]
LINHAS = [l for l in ler_linhas(DADOS / "alimentandos_programa.DBK") if l.startswith("35")]
MARIA, PEDRO, ANA = ITENS


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "alimentandos_programa.DBK")


def gravar(arquivo, *itens):
    campos, erros = alimentandos.validar(list(itens), CPF)
    assert erros == []
    return alimentandos.inserir(arquivo, list(itens), campos)


@pytest.mark.parametrize(("item", "chave", "linha_do_programa"),
                         [(i, n, l) for n, (i, l) in enumerate(zip(ITENS, LINHAS, strict=True), start=1)],
                         ids=["decisao_judicial", "escritura_publica", "ambos_exterior"])
def test_linha_igual_a_gravada_pelo_programa(item, chave, linha_do_programa):
    campos, erros = validar_item(item, CPF)
    assert erros == []
    assert montar_linha(campos, CPF, chave) == linha_do_programa


@pytest.mark.parametrize(("mudanca", "erro"), [
    ({"nome": "Maria - Teste"}, "'nome': só letras e espaços"),
    ({"cpf": None}, "campo obrigatório 'cpf' não informado"),
    ({"cpf": "770.396.770-08"}, "'cpf': o alimentando não pode ser o próprio declarante"),
    ({"residente": "Portugal"}, "'residente': esperado \"brasil\" ou \"exterior\""),
    ({"alimentando_de": "333.444.555-08"}, "'alimentando_de': não pode ser o próprio alimentando"),
    ({"decisao_judicial": None}, "informe 'decisao_judicial', 'escritura_publica' ou os dois"),
    ({"decisao_judicial": {"processo": "1"}}, "campo obrigatório 'decisao_judicial.data' não informado"),
    ({"decisao_judicial": {"data": "2011-01-01"}}, "'decisao_judicial.data': deve estar entre a data de nascimento e 31/12/2025"),
    ({"decisao_judicial": {"data": "2026-01-02"}}, "'decisao_judicial.data': deve estar entre a data de nascimento e 31/12/2025"),
    ({"decisao_judicial": {"data": "2024-02-10", "uf": "XX"}}, "'decisao_judicial.uf': esperada a sigla de uma UF"),
    ({"decisao_judicial": {"data": "2024-02-10", "juiz": "X"}}, "campo desconhecido 'decisao_judicial.juiz'"),
    ({"parentesco": "filha"}, "campo desconhecido 'parentesco'"),
])
def test_validacao(mudanca, erro):
    item = {k: v for k, v in {**MARIA, **mudanca}.items() if v is not None}
    _, erros = validar_item(item, CPF)
    assert len(erros) == 1 and erros[0].startswith(erro), erros


def test_validacao_da_escritura():
    item = {**PEDRO, "escritura_publica": {**PEDRO["escritura_publica"], "cnpj_cartorio": "00.000.000/0001-92",
                                           "cod_municipio": "71070"}}
    _, erros = validar_item(item, CPF)
    assert erros == ["'escritura_publica.cnpj_cartorio': CNPJ (14 dígitos) inválido",
                     "'escritura_publica.cod_municipio': esperado o código do município com até 4 dígitos"]


def test_insere_com_chave_sequencial():
    arquivo = dbk_do_programa()
    arquivo.linhas = [l for l in arquivo.linhas if not l.startswith("35")]
    resultado = gravar(arquivo, *ITENS)
    assert resultado.novos == [1, 2, 3]
    assert arquivo.linhas == dbk_do_programa().linhas


def test_alimentando_importado_recebe_nascimento_e_processo():
    """A importação traz a alimentanda sem data de nascimento e sem tipo de processo."""
    arquivo = ArquivoDBK.ler(DADOS / "pagamentos_importados.DBK")
    (importada,) = arquivo.linhas_do_tipo("35")
    assert Registro35.DATA_NASCIMENTO.ler(importada) == "00000000" and not Registro35.TIPO_PROCESSO.ler(importada).strip()
    resultado = gravar(arquivo, MARIA)
    assert resultado.encontrados == [1] and resultado.diferentes == []
    (atualizada,) = arquivo.linhas_do_tipo("35")
    assert atualizada[19:] [:60] == importada[19:][:60]                    # nome mantido
    assert atualizada[:-10] == LINHAS[0][:-10] and atualizada == LINHAS[0]  # igual à digitada no programa


def test_campo_diferente_fica_e_gera_aviso(caplog):
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, {**MARIA, "residente": "exterior",
                                 "decisao_judicial": {**MARIA["decisao_judicial"], "vara": "2"}})
    assert resultado.diferentes == [1] and arquivo.linhas == antes
    assert "residente, decisao_judicial.vara" in caplog.text


def test_alimentando_de_fora_do_dbk_vai_para_revisao():
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, {**MARIA, "cpf": "456.456.456-00", "alimentando_de": "222.333.444-05"})
    assert resultado.revisao == [1] and arquivo.linhas == antes


def test_cpf_de_dependente_vai_para_revisao():
    arquivo = ArquivoDBK.ler(DADOS / "pagamentos_importados.DBK")
    resultado = gravar(arquivo, {**MARIA, "cpf": "222.333.444-05"})
    assert resultado.revisao == [1]


def test_relatorio_lembra_a_confirmacao_e_nao_tem_dados():
    resultado = gravar(dbk_do_programa(), MARIA)
    texto = "\n".join(t for _, t in alimentandos.relatorio(resultado))
    assert "1 encontrado(s), 0 novo(s), 0 para revisão" in texto
    assert "itens da ficha): 2, 3" in texto and "Estou ciente" in texto
    assert not any(d in texto for d in ("33344455508", "MARIA", "2012"))


def test_main_grava_alimentando_e_pensao_dele(tmp_path):
    from test_fichas_e_leiaute import rodar_main
    pensao = {"codigo": "30", "cpf_dependente_alimentando": MARIA["cpf"], "valor_pago": "1200.00"}
    execucao, saida = rodar_main(tmp_path, {"cpf": CPF, "alimentandos": [MARIA], "pagamentos": [pensao]})
    assert execucao.returncode == 0, execucao.stderr
    assert "Alimentandos: 0 encontrado(s), 1 novo(s)" in execucao.stderr
    assert "Pagamentos Efetuados: 0 preenchido(s), 1 novo(s), 0 para revisão" in execucao.stderr
    assert ArquivoDBK.ler(saida).linhas_do_tipo("35") == [LINHAS[0]]
