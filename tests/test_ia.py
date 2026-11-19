"""Etapa de IA (src/irpf_bot_2027/ia/, docs/adr/0029), com um provedor falso: nenhum teste chama a API."""

import contextlib
import json

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.exportar import exportar_dbk
from irpf_bot_2027.ia.etapa import executar, montar_pedido, prompt_de_sistema
from irpf_bot_2027.ia.provedores import Conversa, ErroIA, Provedor, esquema_para_a_api
from irpf_bot_2027.ia.pseudonimizacao import desfazer, pseudonimizar

CPF = "77039677008"


class ConversaFalsa(Conversa):
    def __init__(self, respostas: list[str], registro: list):
        self.respostas, self.registro = list(respostas), registro

    def iniciar(self, sistema, pedido, esquema):
        self.registro.append(("iniciar", sistema, pedido))
        return self.respostas.pop(0)

    def corrigir(self, erros):
        self.registro.append(("corrigir", erros))
        return self.respostas.pop(0)


class ProvedorFalso(Provedor):
    nome = "falso"

    def __init__(self, *respostas):
        self.respostas, self.registro = respostas, []

    @contextlib.contextmanager
    def sessao(self, documentos):
        self.registro.append(("documentos", [d.name for d in documentos]))
        yield ConversaFalsa(self.respostas, self.registro)


def exportado(nome: str) -> dict:
    return exportar_dbk(ArquivoDBK.ler(DADOS / nome))


# --- pseudonimização ---

@pytest.mark.parametrize("nome", ["pagamentos_programa.DBK", "dependentes_programa.DBK", "alimentandos_programa.DBK",
                                  "contas_programa.DBK", "veiculo_programa.DBK", "programa_com_imovel.DBK"])
def test_pseudonimizar_e_desfazer_volta_ao_original(nome):
    original = exportado(nome)
    pseudo, tabela = pseudonimizar(original)
    assert desfazer(pseudo, tabela) == (original, [])


def test_dados_de_pessoa_fisica_nao_vao_para_a_ia():
    pseudo, _ = pseudonimizar(exportado("pagamentos_programa.DBK"))
    texto = json.dumps(pseudo)
    for dado in (CPF, "22233344405", "33344455508", "44455566619", "JOAO TESTE", "MARIA TESTE", "MEDICO TESTE",
                 "LOCADOR TESTE"):
        assert dado not in texto
    assert "33000167000101" in texto and "OPERADORA TESTE" in texto        # CNPJ e empresa ficam abertos


def test_conta_veiculo_e_imovel_viram_codigo():
    for nome, dados in (("contas_programa.DBK", ("98765",)), ("veiculo_programa.DBK", ("12345678900", "PT-ABC"))):
        texto = json.dumps(pseudonimizar(exportado(nome))[0])
        assert not any(d in texto for d in dados), nome


def test_mesmo_dado_mesmo_codigo_e_numeros_no_texto():
    pseudo, tabela = pseudonimizar({"cpf": CPF, "bens": [{"discriminacao": "Conta 12345-6 no banco", "cnpj_cpf": "1"},
                                                          {"pertence_a": {"tipo": "D", "cpf": "770.396.770-08"}}]})
    assert pseudo["bens"][1]["pertence_a"]["cpf"] == pseudo["cpf"]          # com e sem pontuação
    assert "12345" not in pseudo["bens"][0]["discriminacao"]
    assert desfazer(pseudo, tabela)[0]["bens"][0]["discriminacao"] == "Conta 12345-6 no banco"


def test_codigo_inventado_e_apontado():
    _, tabela = pseudonimizar({"cpf": CPF})
    assert desfazer({"cpf": "CPF_0001", "x": "CPF_0099"}, tabela) == ({"cpf": CPF, "x": "CPF_0099"}, ["CPF_0099"])


# --- provedor ---

def test_esquema_para_a_api_tira_o_que_a_saida_estruturada_nao_aceita():
    esquema = {"$schema": "x", "type": "object", "properties": {"a": {"type": "string", "minLength": 1, "maxLength": 9,
                                                                    "pattern": "^a$"}}}
    assert esquema_para_a_api(esquema) == {"type": "object", "properties": {"a": {"type": "string", "pattern": "^a$"}}}


def test_prompt_e_pedido():
    assert prompt_de_sistema().startswith("## Papel")
    pseudo, _ = pseudonimizar(exportado("dependentes_programa.DBK"))
    pedido = montar_pedido(pseudo, [DADOS / "informe.pdf"])
    assert "- informe.pdf" in pedido and "77788899941" not in pedido and '"cpf": "CPF_0001"' in pedido


# --- etapa completa ---

def resposta_com_o_filho(**mudancas) -> str:
    """O que uma IA devolveria: o filho do DBK (com os códigos), completado pelos documentos."""
    pseudo, _ = pseudonimizar(exportado("dependentes_programa.DBK"))
    filho = next(d for d in pseudo["dependentes"] if d["tipo"] == "21")
    return json.dumps({"cpf": pseudo["cpf"], "dependentes": [{**filho, **mudancas, "origem": [{"documento": "rg.pdf"}]}],
                       "pendencias": [{"descricao": "saldo divergente entre extrato e informe"}]})


def test_resposta_valida_volta_com_os_dados_reais(tmp_path):
    provedor = ProvedorFalso(resposta_com_o_filho())
    dados = executar(DADOS / "dependentes_programa.DBK", [tmp_path / "rg.pdf"], provedor)
    (filho,) = dados["dependentes"]
    assert dados["cpf"] == CPF and filho["cpf"] == "77788899941" and filho["nome"] == "FILHO TESTE"
    assert filho["dbk"] == {"chave": 2} and len(dados["pendencias"]) == 1
    assert [r[0] for r in provedor.registro] == ["documentos", "iniciar"]


def test_erros_voltam_para_a_ia_sem_dados_do_cliente(tmp_path):
    provedor = ProvedorFalso(resposta_com_o_filho(data_nascimento="10/05/2015"), resposta_com_o_filho())
    dados = executar(DADOS / "dependentes_programa.DBK", [], provedor)
    assert dados["dependentes"][0]["data_nascimento"] == "2015-05-10"
    (_, erros), = [r for r in provedor.registro if r[0] == "corrigir"]
    assert "dependentes/0/data_nascimento" in erros
    assert "77788899941" not in erros and "FILHO" not in erros and "10/05/2015" not in erros


def test_erro_da_validacao_do_bot_tambem_volta(tmp_path):
    provedor = ProvedorFalso(resposta_com_o_filho(data_nascimento="2001-01-01"), resposta_com_o_filho())
    executar(DADOS / "dependentes_programa.DBK", [], provedor)
    (_, erros), = [r for r in provedor.registro if r[0] == "corrigir"]
    assert "Dependentes > dependente 1: 'data_nascimento': o tipo 21 exige nascimento a partir de 01/01/2003" in erros


def test_codigo_inventado_volta_para_a_ia(tmp_path):
    provedor = ProvedorFalso(resposta_com_o_filho(cpf="CPF_0099"), resposta_com_o_filho())
    executar(DADOS / "dependentes_programa.DBK", [], provedor)
    (_, erros), = [r for r in provedor.registro if r[0] == "corrigir"]
    assert "o código CPF_0099 não existe no JSON do DBK" in erros


def test_desiste_depois_das_tentativas():
    provedor = ProvedorFalso("não é JSON", "{}", "{}")
    with pytest.raises(ErroIA, match="em 3 tentativa"):
        executar(DADOS / "dependentes_programa.DBK", [], provedor, tentativas=3)
