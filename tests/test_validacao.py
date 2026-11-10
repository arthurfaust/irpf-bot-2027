"""Comportamento atual da validação de um bem do JSON."""

import json
from decimal import Decimal

import pytest

from conftest import DADOS
from irpf_bot_2027.fichas.bens.validacao import validar_bem

BENS = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]
BITCOIN, APARTAMENTO = BENS

@pytest.mark.parametrize("bem", BENS, ids=["bitcoin", "apartamento"])
def test_exemplo_e_valido(bem):
    _, erros = validar_bem(bem)
    assert erros == []

def test_apartamento_converte_campos_do_bloco():
    campos, _ = validar_bem(APARTAMENTO)
    assert campos["UNIDADE_AREA"] == 0
    assert campos["REGISTRADO_CARTORIO"] == 1
    assert campos["DATA_AQUISICAO"] == "10052019"

@pytest.mark.parametrize(
    ("bem", "trecho_do_erro"),
    [
        ({**BITCOIN, "codigo": "05"}, "não existe"),
        ({**BITCOIN, "cripto": {"autocustodiante": True, "cnpj_custodiante": "12345678000199"}}, "quando é autocustodiante"),
        ({**BITCOIN, "cripto": {"autocustodiante": True, "altcoin": "ETH"}}, "'cripto.altcoin' não se aplica"),
        ({**APARTAMENTO, "pais": "111"}, "'imovel.iptu' não se aplica"),
        ({**APARTAMENTO, "imovel": {"vagas": 2}}, "campo desconhecido 'imovel.vagas'"),
        ({**APARTAMENTO, "veiculo": {"placa": "X"}}, "bloco desconhecido 'veiculo'"),
        ({**APARTAMENTO, "imovel": {"unidade": "metros"}}, 'esperado "m2" ou "ha"'),
        ({**BITCOIN, "cripto": {"autocustodiante": "nao"}}, "esperado true ou false"),
        ({**BITCOIN, "pertence_a": {"tipo": "X"}}, 'esperado "T" ou "D"'),
    ],
    ids=["codigo-inexistente", "cnpj-autocustodiante", "altcoin-no-bitcoin", "iptu-no-exterior",
         "chave-desconhecida", "bloco-desconhecido", "unidade-invalida", "booleano-como-texto", "tipo-invalido"],
)
def test_bem_invalido_e_barrado(bem, trecho_do_erro):
    _, erros = validar_bem(bem)
    assert any(trecho_do_erro in erro for erro in erros), erros


def sem(bem: dict, chave: str) -> dict:
    return {k: v for k, v in bem.items() if k != chave}


@pytest.mark.parametrize(
    "chave", ["grupo", "codigo", "pais", "discriminacao", "situacao_anterior", "situacao_atual"]
)
def test_campo_obrigatorio_ausente_e_barrado(chave):
    _, erros = validar_bem(sem(APARTAMENTO, chave))
    assert f"campo obrigatório '{chave}' não informado" in erros


@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_discriminacao_vazia_e_barrada(vazio):
    _, erros = validar_bem({**APARTAMENTO, "discriminacao": vazio})
    assert "campo obrigatório 'discriminacao' não informado" in erros


def test_usufruto_e_opcional():
    _, erros = validar_bem(sem(BITCOIN, "usufruto"))
    assert erros == []


def test_campo_de_primeiro_nivel_desconhecido_e_barrado():
    """Um nome errado (ex.: com cedilha) não pode ser ignorado: o valor sumiria sem aviso."""
    bem = {**sem(APARTAMENTO, "situacao_atual"), "situaçao_atual": "350000.00"}
    _, erros = validar_bem(bem)
    assert "campo desconhecido 'situaçao_atual'" in erros
    assert "campo obrigatório 'situacao_atual' não informado" in erros


def test_todos_os_erros_aparecem_de_uma_vez():
    bem = {"grupo": "01", "codigo": "11", "pais": "105", "imovel": {"vagas": 1}}
    _, erros = validar_bem(bem)
    assert len(erros) == 4            # vagas + discriminacao + situacao_anterior + situacao_atual


def test_campos_do_primeiro_nivel_sao_convertidos():
    campos, _ = validar_bem(BITCOIN)
    assert campos["GRUPO"] == "08"
    assert campos["VALOR_ATUAL"] == Decimal("2000.00")
    assert campos["USUFRUTO"] == 0


@pytest.mark.parametrize(
    ("bem", "erro"),
    [
        ({**BITCOIN, "situacao_atual": "2.000,00"},
         "'situacao_atual': use ponto como separador decimal, sem separador de milhar: \"1234.56\""),
        ({**BITCOIN, "situacao_anterior": "-1.00"}, "'situacao_anterior': o valor não pode ser negativo"),
        ({**APARTAMENTO, "imovel": {**APARTAMENTO["imovel"], "area": "75,5"}},
         "'imovel.area': use ponto como separador decimal, sem separador de milhar: \"1234.5\""),
    ],
    ids=["virgula-na-situacao", "situacao-negativa", "virgula-na-area"],
)
def test_valor_em_formato_errado_e_barrado(bem, erro):
    _, erros = validar_bem(bem)
    assert erros == [erro]


def test_valor_como_numero_do_json_e_aceito():
    campos, erros = validar_bem({**BITCOIN, "situacao_anterior": 1000, "situacao_atual": 2000.5})
    assert erros == []
    assert campos["VALOR_ATUAL"] == Decimal("2000.5")
