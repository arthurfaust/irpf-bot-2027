"""Bloco conta: poupança (04/01) e conta corrente ou conta pagamento (06/01).

contas_programa.DBK foi gravado pelo programa IRPF 2026 em 13/11/2026 com os mesmos 6 bens de
contas.json, digitados na tela (CPF fictício).
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.fichas.bens.ficha import montar_linha
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CPF = "77039677008"
BENS = json.loads((DADOS / "contas.json").read_text(encoding="utf-8"))["bens"]
LINHAS_DO_PROGRAMA = [linha for linha in ler_linhas(DADOS / "contas_programa.DBK") if linha.startswith("27")]
CONTA_BB = BENS[0]


def com_conta(bem: dict, **conta) -> dict:
    """Cópia do bem com o bloco conta alterado (valor None remove a chave)."""
    novo = {**bem["conta"], **conta}
    return {**bem, "conta": {k: v for k, v in novo.items() if v is not None}}


@pytest.mark.parametrize(("bem", "linha_do_programa"), list(zip(BENS, LINHAS_DO_PROGRAMA, strict=True)),
                         ids=[bem["discriminacao"] for bem in BENS])
def test_linha_igual_a_gravada_pelo_programa(bem, linha_do_programa):
    campos, erros = validar_bem(bem)
    assert erros == []
    chave = int(Registro27.CHAVE.ler(linha_do_programa))
    assert montar_linha(bem, campos, CPF, chave) == linha_do_programa


def test_conta_da_caixa_ganha_zeros_ate_12_digitos():
    campos, _ = validar_bem(BENS[1])
    assert campos["CONTA"] == "000000004321"


def test_conta_dos_outros_bancos_fica_como_veio():
    campos, _ = validar_bem(com_conta(CONTA_BB, conta="0098765"))
    assert campos["CONTA"] == "0098765"


def test_banco_e_agencia_aceitam_numero_e_completam_com_zeros():
    campos, erros = validar_bem(com_conta(CONTA_BB, banco=1, agencia=12))
    assert erros == []
    assert Registro27.BANCO.formatar(campos["BANCO"]) == "001"
    assert Registro27.AGENCIA.formatar(campos["AGENCIA"]) == "0012"


@pytest.mark.parametrize("campo", ["banco", "agencia", "conta", "dv"])
def test_campos_da_conta_sao_obrigatorios(campo):
    _, erros = validar_bem(com_conta(CONTA_BB, **{campo: None}))
    assert erros == [f"'conta.{campo}' é obrigatório para 06/01 (Depósito em conta corrente ou conta pagamento) no Brasil"]


@pytest.mark.parametrize(
    ("alteracao", "erro"),
    [
        ({"conta": "98765-4"}, "'conta.conta': esperado o número da conta, só com números; o dígito verificador vai em 'conta.dv'"),
        ({"agencia": "1234-5"}, "'conta.agencia': esperado o número da agência, só com números, sem o dígito da agência"),
        ({"agencia": "12345"}, "'conta.agencia': esperado o número da agência, com até 4 dígitos"),
        ({"banco": "1234"}, "'conta.banco': esperado o código do banco (ex.: \"001\"), com até 3 dígitos"),
        ({"banco": "999"}, "'conta.banco': banco 999 não existe na tabela de bancos do programa"),
        ({"dv": "12X"}, "'conta.dv': esperado o dígito verificador com 1 ou 2 letras ou números (ex.: \"7\" ou \"X\")"),
        ({"dv": "-"}, "'conta.dv': esperado o dígito verificador com 1 ou 2 letras ou números (ex.: \"7\" ou \"X\")"),
        ({"conta": "1" * 21}, "'conta.conta': esperado o número da conta, com até 20 dígitos"),
        ({"conta_pagamento": "sim"}, "'conta.conta_pagamento': esperado true ou false, veio 'sim'"),
    ],
)
def test_formato_invalido(alteracao, erro):
    _, erros = validar_bem(com_conta(CONTA_BB, **alteracao))
    assert erros == [erro]


def test_conta_da_caixa_com_mais_de_12_digitos():
    _, erros = validar_bem(com_conta(BENS[2], conta="1234567890123"))
    assert erros == ["'conta.conta': na Caixa (banco 104) a conta tem no máximo 12 dígitos"]


def test_mensagens_nao_repetem_os_numeros_da_conta():
    _, erros = validar_bem(com_conta(CONTA_BB, agencia="98-76", conta="5555-1", dv="#"))
    assert len(erros) == 3
    assert not any("98-76" in erro or "5555" in erro or "#" in erro for erro in erros)


def test_conta_pagamento_so_existe_na_conta_corrente():
    _, erros = validar_bem(com_conta(BENS[1], conta_pagamento=True))
    assert erros == ["'conta.conta_pagamento' não se aplica a 04/01 (Depósito em conta poupança) no Brasil"]


def test_conta_pagamento_marcada_grava_1():
    campos, erros = validar_bem(com_conta(BENS[5], conta_pagamento=True))
    assert erros == []
    linha = montar_linha(BENS[5], campos, CPF, 1)
    assert Registro27.CONTA_PAGAMENTO.ler(linha) == "1"


def test_bloco_conta_em_bem_sem_conta_bancaria():
    fundo = {"grupo": "07", "codigo": "01", "pais": "105", "cnpj_cpf": "11.222.333/0001-81", "discriminacao": "FUNDO",
             "situacao_anterior": "0.00", "situacao_atual": "1.00", "conta": CONTA_BB["conta"]}
    _, erros = validar_bem(fundo)
    assert len(erros) == 4
    assert all("não se aplica a 07/01" in erro for erro in erros)
