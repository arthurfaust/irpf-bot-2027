"""Comportamento atual da validação de um bem do JSON."""

import json

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
