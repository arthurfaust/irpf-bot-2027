"""JSON Schema da entrada (src/irpf_bot_2027/esquema.py, docs/adr/0028).

O arquivo em docs/ia/ precisa estar em dia com o código, e tudo o que o bot aceita precisa passar no
esquema (o esquema não pode recusar o que o bot aceita).
"""

import json

import jsonschema
import pytest

from conftest import DADOS, RAIZ
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.esquema import gerar
from irpf_bot_2027.exportar import exportar_dbk

PASTA = RAIZ / "docs" / "ia"
VALIDADOR = jsonschema.Draft202012Validator(gerar())


@pytest.mark.parametrize(("nome", "anonimizado"), [("esquema_entrada.json", False), ("esquema_ia.json", True)])
def test_esquemas_validos_e_em_dia_com_o_codigo(nome, anonimizado):
    jsonschema.Draft202012Validator.check_schema(gerar(anonimizado))
    assert json.loads((PASTA / nome).read_text(encoding="utf-8")) == gerar(anonimizado), \
        "rode: uv run irpf-bot-2027-esquema docs/ia"


def test_esquema_da_ia_aceita_codigos_da_anonimizacao():
    ia = jsonschema.Draft202012Validator(gerar(anonimizado=True))
    dados = {"cpf": "CPF_0001",
             "dependentes": [{"tipo": "21", "nome": "NOME_0002", "cpf": "CPF_0003", "data_nascimento": "2015-05-10"}],
             "bens": [{"grupo": "02", "codigo": "01", "pais": "105", "discriminacao": "Carro", "situacao_anterior": "0.00",
                       "situacao_atual": "1.00", "veiculo": {"renavam": "RENAVAM_0004"}}]}
    assert list(ia.iter_errors(dados)) == []
    assert list(VALIDADOR.iter_errors(dados))               # o do bot recusa: o JSON precisa voltar aos dados reais
    errado = {**dados, "bens": [{**dados["bens"][0], "situacao_atual": "1.000,00"}]}
    assert list(ia.iter_errors(errado))                     # valores continuam conferidos


@pytest.mark.parametrize("arquivo", ["dados.example.json", "pagamentos.json", "dependentes.json",
                                     "alimentandos.json", "rendpj.json", "bens.json"])
def test_jsons_aceitos_pelo_bot_passam_no_esquema(arquivo):
    caminho = RAIZ / "data" / arquivo if arquivo == "dados.example.json" else DADOS / arquivo
    assert list(VALIDADOR.iter_errors(json.loads(caminho.read_text(encoding="utf-8")))) == []


@pytest.mark.parametrize("dbk", ["contas_programa.DBK", "bolsa_programa.DBK", "veiculo_programa.DBK",
                                 "exterior_programa.DBK", "dependentes_programa.DBK", "alimentandos_programa.DBK",
                                 "rendpj_programa.DBK"])
def test_json_exportado_passa_no_esquema(dbk):
    assert list(VALIDADOR.iter_errors(exportar_dbk(ArquivoDBK.ler(DADOS / dbk)))) == []


@pytest.mark.parametrize(("mudanca", "caminho"), [
    ({"bens": [{"grupo": "06", "codigo": "01", "pais": "105", "discriminacao": "X", "situacao_anterior": "1.00",
                "situacao_atual": "1.000,00"}]}, ["bens", 0, "situacao_atual"]),
    ({"pagamentos": [{"codigo": "40", "valor_pago": "1.00"}]}, ["pagamentos", 0, "codigo"]),
    ({"dependentes": [{"tipo": "21", "nome": "A", "cpf": "222.333.444-05", "data_nascimento": "2015-05-10",
                       "parentesco": "filho"}]}, ["dependentes", 0]),
    ({"rendimentos_pj": [{"dbk": {"chave": 1}}]}, ["rendimentos_pj", 0, "dbk"]),
    ({"pendencias": [{"origem": [{"documento": "a.pdf"}]}]}, ["pendencias", 0]),
])
def test_esquema_recusa_o_que_o_bot_recusa(mudanca, caminho):
    erros = list(VALIDADOR.iter_errors({"cpf": "770.396.770-08", **mudanca}))
    assert any(list(e.absolute_path)[:len(caminho)] == caminho for e in erros), [e.message for e in erros]


def test_bot_aceita_origem_e_pendencias(tmp_path):
    from test_fichas_e_leiaute import rodar_main
    item = json.loads((DADOS / "dependentes.json").read_text(encoding="utf-8"))["dependentes"][0]
    dados = {"cpf": "77039677008", "dependentes": [{**item, "origem": [{"documento": "rg.pdf", "pagina": 1}]}],
             "pendencias": [{"descricao": "conflito de saldo", "origem": [{"documento": "extrato.pdf"}]}]}
    assert list(VALIDADOR.iter_errors(dados)) == []
    execucao, _ = rodar_main(tmp_path, dados)
    assert execucao.returncode == 0, execucao.stderr
    assert "1 pendência(s) da etapa de IA" in execucao.stderr
    assert "rg.pdf" not in execucao.stderr and "conflito" not in execucao.stderr


@pytest.mark.parametrize("origem", [[], "rg.pdf", [{"documento": ""}], [{"documento": "a", "pagina": 0}],
                                    [{"arquivo": "a"}]])
def test_bot_recusa_origem_fora_do_formato(origem):
    from irpf_bot_2027.fichas import dependentes
    item = json.loads((DADOS / "dependentes.json").read_text(encoding="utf-8"))["dependentes"][0]
    _, erros = dependentes.validar([{**item, "origem": origem}], "77039677008")
    assert erros and "'origem'" in erros[0]
