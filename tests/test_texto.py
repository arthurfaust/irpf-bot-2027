"""Normalização de texto e conferência de formato dos campos do bem."""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.fichas.bens.validacao import validar_bem

BITCOIN, APARTAMENTO = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Conta – banco “X”", 'Conta - banco "X"'),
        ("Ações do ‘Banco’…", "Ações do 'Banco'..."),
        ("linha 1\nlinha 2\r\n\tlinha 3", "linha 1 linha 2 linha 3"),
        ("  muitos   espaços  ", "muitos espaços"),
        ("água", "água"),                     # acento separado da letra
        ("Casa na praia", "Casa na praia"),    # espaço não separável
        ("Apartamento 101, Curitiba-PR", "Apartamento 101, Curitiba-PR"),
    ],
)
def test_normalizar_texto(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


def test_caracteres_fora_do_latin1():
    assert caracteres_fora_do_latin1("ok ção 😀 € 😀") == ["😀", "€"]


def test_texto_com_aspas_curvas_e_travessao_e_aceito_e_normalizado():
    campos, erros = validar_bem({**BITCOIN, "discriminacao": "0,05 BTC – corretora “X”"})
    assert erros == []
    assert campos["DISCRIMINACAO"] == '0,05 BTC - corretora "X"'


def test_quebra_de_linha_na_discriminacao_vira_espaco():
    campos, erros = validar_bem({**BITCOIN, "discriminacao": "linha 1\nlinha 2"})
    assert erros == []
    assert campos["DISCRIMINACAO"] == "linha 1 linha 2"


def test_caractere_sem_equivalente_e_barrado():
    _, erros = validar_bem({**BITCOIN, "discriminacao": "Bitcoin 🚀 na corretora €"})
    assert erros == ["'discriminacao': caractere(s) não aceito(s) pelo programa: '🚀' (U+1F680), '€' (U+20AC)"]


def test_discriminacao_no_limite_e_aceita():
    _, erros = validar_bem({**BITCOIN, "discriminacao": "a" * 512})
    assert erros == []


def test_discriminacao_maior_que_o_campo_e_barrada():
    _, erros = validar_bem({**BITCOIN, "discriminacao": "a" * 513})
    assert erros == ["'discriminacao': tem 513 caracteres; o máximo é 512"]


def test_texto_de_bloco_maior_que_o_campo_e_barrado():
    _, erros = validar_bem({**APARTAMENTO, "imovel": {**APARTAMENTO["imovel"], "numero": "1234567"}})
    assert erros == ["'imovel.numero': tem 7 caracteres; o máximo é 6"]


def test_valor_grande_demais_e_barrado():
    _, erros = validar_bem({**BITCOIN, "situacao_atual": "123456789012.00"})
    assert erros == ["'situacao_atual': valor inválido ou grande demais para o campo (número de 13 posições com 2 decimais)"]


def test_mensagem_de_erro_nao_repete_o_texto_do_cliente():
    _, erros = validar_bem({**BITCOIN, "discriminacao": "Conta do Fulano de Tal " + "x" * 600})
    assert all("Fulano" not in erro for erro in erros)
