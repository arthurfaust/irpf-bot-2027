"""Ficha Rendimentos Tributáveis Recebidos de PJ pelo Titular (registro 21, docs/adr/0020).

rendpj_programa.DBK foi gravado pelo programa IRPF 2026 em 17/11/2026 com as mesmas 3 fontes de
rendpj.json, digitadas na tela (CPF fictício).
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.comum.documentos import cnpj_valido, cpf_valido
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import rendimentos_pj
from irpf_bot_2027.fichas.rendimentos_pj.ficha import montar_linha, validar_item
from irpf_bot_2027.leiautes.irpf2026.registro21 import Registro21

CPF = "77039677008"
FONTES = json.loads((DADOS / "rendpj.json").read_text(encoding="utf-8"))["rendimentos_pj"]
LINHAS = [l for l in ler_linhas(DADOS / "rendpj_programa.DBK") if l.startswith("21")]
UM, DOIS, PF = FONTES


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "rendpj_programa.DBK")


def gravar(arquivo, *fontes):
    campos, erros = rendimentos_pj.validar(list(fontes), CPF)
    assert erros == []
    return rendimentos_pj.inserir(arquivo, list(fontes), campos)


def zerar(arquivo: ArquivoDBK, ordem: int, nome_tambem: bool = False) -> None:
    """Deixa a fonte nº `ordem` do DBK sem valores, como vem da importação da declaração anterior."""
    posicao = arquivo.indices("21")[ordem - 1]
    linha = arquivo.linhas[posicao]
    for nome in ("RENDIMENTOS", "CONTRIBUICAO", "IMPOSTO", "DECIMO_TERCEIRO", "IRRF_DECIMO_TERCEIRO"):
        linha = getattr(Registro21, nome).gravar(linha, 0)
    if nome_tambem:
        linha = Registro21.NOME_PAGADOR.gravar(linha, "")
    arquivo.substituir(posicao, Registro21.gravar_cod_controle(linha))


# --- leiaute e validação ---

@pytest.mark.parametrize(("fonte", "linha_do_programa"), list(zip(FONTES, LINHAS, strict=True)),
                         ids=["cnpj_completo", "valores_zerados", "cpf"])
def test_linha_igual_a_gravada_pelo_programa(fonte, linha_do_programa):
    campos, erros = validar_item(fonte, CPF)
    assert erros == []
    assert montar_linha(campos, CPF) == linha_do_programa


def test_controle_das_linhas_do_programa():
    assert all(Registro21.gravar_cod_controle(l) == l for l in LINHAS)


@pytest.mark.parametrize(("mudanca", "erro"), [
    ({"cnpj_cpf": "33.000.167/0001-02"}, "'cnpj_cpf': CPF (11 dígitos) ou CNPJ (14 dígitos) inválido"),
    ({"cnpj_cpf": "123"}, "'cnpj_cpf': CPF (11 dígitos) ou CNPJ (14 dígitos) inválido"),
    ({"cnpj_cpf": "770.396.770-08"}, "'cnpj_cpf': a fonte pagadora não pode ser o próprio declarante"),
    ({"rendimentos": "-1.00"}, "'rendimentos': o valor não pode ser negativo"),
    ({"imposto_retido": "1.000,00"}, "'imposto_retido': use ponto como separador decimal, sem separador de milhar: \"1234.56\""),
    ({"nome": "X" * 61}, "'nome': tem 61 caracteres; o máximo é 60"),
    ({"nome": ""}, "campo obrigatório 'nome' não informado"),
    ({"decimo_terceiro": None}, "campo obrigatório 'decimo_terceiro' não informado"),
    ({"salario": "1.00"}, "campo desconhecido 'salario'"),
    ({"rendimentos": "0.00", "contribuicao_previdenciaria": "0", "imposto_retido": "0.00", "decimo_terceiro": "0.00"},
     "rendimentos, contribuição previdenciária, 13º salário e imposto retido estão todos zerados "
     "(o programa acusa erro \"Faltam valores\")"),
])
def test_validacao(mudanca, erro):
    fonte = {k: v for k, v in {**UM, **mudanca}.items() if v is not None}
    _, erros = validar_item(fonte, CPF)
    assert erros == [erro]


def test_erros_numerados_e_sem_dados():
    _, erros = rendimentos_pj.validar([UM, {**DOIS, "cnpj_cpf": "60.701.190/0001-05"}], CPF)
    assert erros == ["fonte 2: 'cnpj_cpf': CPF (11 dígitos) ou CNPJ (14 dígitos) inválido"]


def test_digitos_verificadores():
    assert cnpj_valido("33000167000101") and cpf_valido("11144477735") and cpf_valido(CPF)
    assert not cnpj_valido("33000167000102") and not cpf_valido("11111111111")


# --- busca ---

def test_fonte_com_valores_no_dbk_vai_para_revisao(caplog):
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, UM)
    assert resultado.revisao == [1] and arquivo.linhas == antes
    assert "a fonte já tem valores no DBK" in caplog.text


def test_fonte_sem_valores_no_dbk_recebe_os_valores_do_json():
    arquivo = dbk_do_programa()
    zerar(arquivo, 1, nome_tambem=True)
    resultado = gravar(arquivo, UM)
    assert resultado.preenchidas == [1] and resultado.novas == []
    assert arquivo.linhas_do_tipo("21")[0] == LINHAS[0]          # igual à linha digitada no programa


def test_fonte_nova_e_inserida_depois_das_outras():
    arquivo = dbk_do_programa()
    nova = {**DOIS, "cnpj_cpf": "00.000.000/0001-91", "nome": "BANCO TESTE"}
    resultado = gravar(arquivo, nova)
    assert resultado.novas == [1]
    tipos = [l[:2] for l in arquivo.linhas]
    assert tipos.count("21") == 4 and tipos.index("24") == tipos.index("21") + 4


def test_duas_fontes_do_json_para_uma_sem_valores_vao_para_revisao():
    arquivo = dbk_do_programa()
    zerar(arquivo, 2)
    resultado = gravar(arquivo, DOIS, {**DOIS, "rendimentos": "1.00"})
    assert resultado.revisao == [1, 2]


def test_relatorio_sem_dados_do_cliente():
    arquivo = dbk_do_programa()
    zerar(arquivo, 3)
    nova = {**DOIS, "cnpj_cpf": "00.000.000/0001-91", "nome": "BANCO TESTE"}
    resultado = gravar(arquivo, UM, nova)
    texto = "\n".join(t for _, t in rendimentos_pj.relatorio(resultado))
    assert "0 preenchida(s), 1 nova(s), 1 para revisão" in texto
    assert "continuam sem valores" in texto and "itens da ficha): 3" in texto
    assert "com valores que não vieram no JSON (itens da ficha): 1, 2" in texto     # a 1 foi para revisão
    assert not any(d in texto for d in ("33000167", "EMPRESA", "BANCO TESTE", "85000"))


# --- main ---

def test_main_grava_rendimentos_e_bens_juntos(tmp_path):
    from test_fichas_e_leiaute import rodar_main
    bens = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]
    execucao, saida = rodar_main(tmp_path, {"cpf": CPF, "rendimentos_pj": [UM], "bens": bens})
    assert execucao.returncode == 0, execucao.stderr
    assert "Rendimentos Tributáveis Recebidos de PJ pelo Titular: 0 preenchida(s), 1 nova(s)" in execucao.stderr
    gravado = ArquivoDBK.ler(saida)
    assert gravado.linhas_do_tipo("21") == [LINHAS[0]]
    assert len(gravado.linhas_do_tipo("27")) == 6
