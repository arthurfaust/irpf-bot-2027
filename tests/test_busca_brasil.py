"""Busca dos bens do Brasil que ainda não tinham chave (docs/adr/0019): imóveis, bens com CNPJ/CPF e
bens sem identificador."""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, identificar

APARTAMENTO = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"][1]
BASE = {"pais": "105", "situacao_anterior": "0.00", "situacao_atual": "100.00"}
CDB = {**BASE, "grupo": "04", "codigo": "02", "cnpj_cpf": "60.701.190/0001-04", "discriminacao": "CDB banco X"}
EMPRESTIMO = {**BASE, "grupo": "05", "codigo": "01", "discriminacao": "Emprestimo a terceiro"}
JOIA = {**BASE, "grupo": "02", "codigo": "06", "discriminacao": "Anel de ouro"}


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def dbk_com(*lista) -> ArquivoDBK:
    """DBK sem bens + os bens lançados (como se viessem da declaração anterior)."""
    base = ArquivoDBK.ler(DADOS / "entrada.DBK")
    arquivo = ArquivoDBK([l for l in base.linhas if l[:2] not in ("27", "37")], base.quebra_no_fim)
    gravar(arquivo, *lista)
    return ArquivoDBK(list(arquivo.linhas), arquivo.quebra_no_fim)


def imovel(**mudancas) -> dict:
    """O apartamento com o bloco imovel alterado (valor None remove a chave)."""
    bloco = {**APARTAMENTO["imovel"], **mudancas}
    return {**APARTAMENTO, "imovel": {k: v for k, v in bloco.items() if v is not None}}


SEM_MATRICULA = {"registrado_cartorio": False, "matricula": None, "cartorio": None}


# --- chaves ---

def test_imovel_pelo_iptu():
    assert chave_busca(validados(APARTAMENTO)[0]) == ("01", "11", "105", "IPTU", "123456")


def test_imovel_sem_iptu_pela_matricula_e_cartorio():
    assert chave_busca(validados(imovel(iptu=None))[0]) == ("01", "11", "105", "MATRICULA", "9999", "1ºRI")


def test_imovel_rural_pelo_cib_e_construcao_pelo_cei():
    rural = {"GRUPO": "01", "CODIGO": "14", "PAIS": "105", "CIB": "1234567-8", "COD_MUNICIPIO": "7535"}
    construcao = {"GRUPO": "01", "CODIGO": "16", "PAIS": "105", "CEI_CNO": "000012345678", "COD_MUNICIPIO": "7535"}
    assert chave_busca(rural) == ("01", "14", "105", "CIB", "12345678")
    assert chave_busca(construcao) == ("01", "16", "105", "CEI_CNO", "12345678")


def test_imovel_sem_registro_nem_matricula_nao_tem_identificador():
    [campos] = validados(imovel(iptu=None, **SEM_MATRICULA))
    assert identificar(campos).sem_identificador


def test_bem_com_cnpj_e_sem():
    cdb, emprestimo = validados(CDB, EMPRESTIMO)
    assert chave_busca(cdb) == ("04", "02", "105", "60701190000104")
    assert identificar(emprestimo).sem_identificador                 # o CPF do devedor é opcional


# --- imóveis ---

def test_imovel_encontrado_pelo_iptu_e_atualizado():
    arquivo = dbk_com(APARTAMENTO)
    assert gravar(arquivo, {**APARTAMENTO, "situacao_atual": "400000.00"}).atualizados == [1]


def test_imovel_do_json_so_com_matricula_e_o_do_dbk_com_iptu_vai_para_revisao(caplog):
    """Mesmo código e município, identificadores diferentes: pode ser o mesmo imóvel."""
    arquivo = dbk_com(APARTAMENTO)
    resultado = gravar(arquivo, imovel(iptu=None))
    assert resultado.revisao == [1]
    assert "imóvel do mesmo código no mesmo município com outro registro ou matrícula" in caplog.text


def test_imovel_de_outro_municipio_e_lancado_como_novo():
    arquivo = dbk_com(APARTAMENTO)
    outro = imovel(iptu="999", cod_municipio="7107", municipio="Sao Paulo", uf="SP", cep="01000000")
    assert gravar(arquivo, outro).novos == [1]


def test_imovel_sem_identificador_com_apartamento_no_dbk_vai_para_revisao():
    arquivo = dbk_com(APARTAMENTO)
    assert gravar(arquivo, imovel(iptu=None, **SEM_MATRICULA)).revisao == [1]


def test_imovel_com_iptu_e_apartamento_sem_identificador_no_dbk_vai_para_revisao():
    arquivo = dbk_com(imovel(iptu=None, **SEM_MATRICULA))
    assert gravar(arquivo, APARTAMENTO).revisao == [1]


# --- bens com CNPJ ---

def test_cdb_encontrado_pelo_cnpj():
    assert gravar(dbk_com(CDB), {**CDB, "situacao_atual": "5.00"}).atualizados == [1]


def test_dois_cdbs_do_mesmo_banco_vao_para_revisao():
    arquivo = dbk_com(CDB)
    resultado = gravar(arquivo, CDB, {**CDB, "discriminacao": "Outro CDB banco X"})
    assert resultado.revisao == [1, 2]


def test_cdb_de_outro_banco_e_lancado_como_novo():
    assert gravar(dbk_com(CDB), {**CDB, "cnpj_cpf": "00.000.000/0001-91"}).novos == [1]


def test_credito_com_cpf_e_credito_sem_cpf_no_dbk_vai_para_revisao():
    arquivo = dbk_com(EMPRESTIMO)
    assert gravar(arquivo, {**EMPRESTIMO, "cnpj_cpf": "770.396.770-08"}).revisao == [1]


# --- sem identificador ---

@pytest.mark.parametrize("bem", [JOIA, EMPRESTIMO], ids=["joia", "credito_sem_cpf"])
def test_sem_identificador_com_bem_igual_no_dbk_vai_para_revisao(bem):
    assert gravar(dbk_com(bem), bem).revisao == [1]


def test_sem_identificador_de_outro_codigo_e_lancado_como_novo():
    quadro = {**JOIA, "codigo": "05", "discriminacao": "Quadro"}
    assert gravar(dbk_com(JOIA), quadro).novos == [1]


def test_relatorio_mostra_o_bem_do_dbk_sem_identificador():
    resultado = gravar(dbk_com(JOIA), CDB)
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "02/06" in texto and "bem sem campo identificador: confira e atualize no programa" in texto
