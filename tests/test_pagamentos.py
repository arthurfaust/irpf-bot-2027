"""Ficha Pagamentos Efetuados (registro 26, docs/adr/0021).

pagamentos_programa.DBK foi gravado pelo programa IRPF 2026 em 18/11/2026 com um dependente (JOAO TESTE),
uma alimentanda (MARIA TESTE) e os mesmos 8 pagamentos de pagamentos.json, digitados na tela
(CPF fictício). O programa grava os pagamentos ordenados pelo código; o JSON segue essa ordem.
"""

import json

import pytest

from conftest import DADOS, ler_linhas
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import pagamentos
from irpf_bot_2027.fichas.pagamentos.ficha import completar, montar_linha, validar_item, vinculado_no_dbk
from irpf_bot_2027.leiautes.irpf2026.registro25 import Registro25
from irpf_bot_2027.leiautes.irpf2026.registro26 import Registro26
from irpf_bot_2027.leiautes.irpf2026.registro35 import Registro35

CPF = "77039677008"
ITENS = json.loads((DADOS / "pagamentos.json").read_text(encoding="utf-8"))["pagamentos"]
LINHAS = [l for l in ler_linhas(DADOS / "pagamentos_programa.DBK") if l.startswith("26")]
INSTRUCAO, MEDICO, EXTERIOR, PLANO, PENSAO, PREVIDENCIA, ALUGUEL, OUTROS = ITENS


def dbk_do_programa() -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / "pagamentos_programa.DBK")


def dbk_sem_pagamentos() -> ArquivoDBK:
    arquivo = dbk_do_programa()
    arquivo.linhas = [l for l in arquivo.linhas if not l.startswith("26")]
    return arquivo


def gravar(arquivo, *itens):
    campos, erros = pagamentos.validar(list(itens), CPF)
    assert erros == []
    return pagamentos.inserir(arquivo, list(itens), campos)


# --- leiaute ---

@pytest.mark.parametrize(("registro", "tipo"), [(Registro25, "25"), (Registro26, "26"), (Registro35, "35")])
def test_tamanho_e_controle_das_linhas_do_programa(registro, tipo):
    linhas = dbk_do_programa().linhas_do_tipo(tipo)
    assert linhas and all(len(l) == registro.TAMANHO for l in linhas)
    assert all(registro.gravar_cod_controle(l) == l for l in linhas)


@pytest.mark.parametrize(("item", "linha_do_programa"), list(zip(ITENS, LINHAS, strict=True)),
                         ids=["instrucao_alimentando", "medico_titular", "exterior", "plano_dependente",
                              "pensao", "previdencia", "aluguel_sem_tipo", "outros"])
def test_linha_igual_a_gravada_pelo_programa(item, linha_do_programa):
    campos, erros = validar_item(item, CPF)
    assert erros == []
    tipo = campos["TIPO_PAGAMENTO"]
    if tipo in ("D", "A"):
        (vinculado,) = vinculado_no_dbk(dbk_do_programa(), tipo, campos["_cpf_vinculado"])
        campos = completar(campos, tipo, vinculado)
    assert montar_linha(campos, CPF) == linha_do_programa


# --- validação ---

@pytest.mark.parametrize(("item", "erro"), [
    ({**MEDICO, "codigo": "40"}, "'codigo': esperado um dos códigos da ficha"),
    ({**MEDICO, "tipo": None}, "campo obrigatório 'tipo' não informado (código 10)"),
    ({**OUTROS, "tipo": "A"}, "'tipo': esperado 'T' ou 'D' (titular, dependente)"),
    ({**ALUGUEL, "tipo": "T"}, "'tipo' não se aplica ao código 70"),
    ({**MEDICO, "tipo": "D"}, "campo obrigatório 'cpf_dependente_alimentando' não informado (código 10)"),
    ({**MEDICO, "cnpj_cpf": "33.000.167/0001-01"}, "'cnpj_cpf': CPF (11 dígitos) inválido"),
    ({**PLANO, "cnpj_cpf": "444.555.666-19"}, "'cnpj_cpf': CNPJ (14 dígitos) inválido"),
    ({**ALUGUEL, "cnpj_cpf": "123"}, "'cnpj_cpf': CPF (11 dígitos) ou CNPJ (14 dígitos) inválido"),
    ({**MEDICO, "cnpj_cpf": "770.396.770-08"}, "'cnpj_cpf': o beneficiário não pode ser o próprio declarante"),
    ({**MEDICO, "tipo": "D", "cpf_dependente_alimentando": "444.555.666-19"},
     "'cnpj_cpf': o beneficiário não pode ser o próprio dependente"),
    ({**EXTERIOR, "cnpj_cpf": "444.555.666-19"}, "'cnpj_cpf' não se aplica ao código 15"),
    ({**EXTERIOR, "pais": None}, "campo obrigatório 'pais' não informado (código 15)"),
    ({**EXTERIOR, "pais": "105"}, "'pais': esperado o código de um país do exterior com até 3 dígitos (ex.: \"249\")"),
    ({**MEDICO, "pais": "249"}, "'pais' não se aplica ao código 10"),
    ({**PENSAO, "nome": "X"}, "'nome' não se aplica ao código 30"),
    ({**PENSAO, "cpf_dependente_alimentando": None}, "campo obrigatório 'cpf_dependente_alimentando' não informado (código 30)"),
    ({**MEDICO, "nome": ""}, "campo obrigatório 'nome' não informado (código 10)"),
    ({**MEDICO, "valor_pago": "0.00"}, "'valor_pago': o valor pago não pode ser zero"),
    ({**MEDICO, "valor_pago": "-1.00"}, "'valor_pago': o valor não pode ser negativo"),
    ({**MEDICO, "parcela_nao_dedutivel": "1500.01"}, "'parcela_nao_dedutivel': maior que o valor pago"),
    ({**ALUGUEL, "parcela_nao_dedutivel": "1.00"}, "'parcela_nao_dedutivel' não se aplica ao código 70"),
    ({**OUTROS, "descricao": None}, "campo obrigatório 'descricao' não informado (código 99)"),
    ({**MEDICO, "salario": "1"}, "campo desconhecido 'salario'"),
])
def test_validacao(item, erro):
    _, erros = validar_item({k: v for k, v in item.items() if v is not None}, CPF)
    assert len(erros) == 1 and erros[0].startswith(erro), erros


def test_99_sem_cpf_cnpj_e_aceito():
    campos, erros = validar_item({k: v for k, v in OUTROS.items() if k != "cnpj_cpf"}, CPF)
    assert erros == [] and "NI_BENEFICIARIO" not in campos


def test_erros_numerados():
    _, erros = pagamentos.validar([MEDICO, {**PLANO, "valor_pago": "0"}], CPF)
    assert erros == ["pagamento 2: 'valor_pago': o valor pago não pode ser zero"]


# --- inserção e busca ---

def test_insere_os_pagamentos_iguais_aos_do_programa():
    arquivo = dbk_sem_pagamentos()
    resultado = gravar(arquivo, *ITENS)
    assert resultado.novos == list(range(1, 9)) and resultado.revisao == []
    assert arquivo.linhas_do_tipo("26") == LINHAS
    assert arquivo.linhas == dbk_do_programa().linhas


def test_insere_na_ordem_do_codigo_como_o_programa():
    """O programa regrava os pagamentos ordenados pelo código e, no mesmo código, na ordem em que
    estavam (roteiro manual, 18/11/2026). O bot insere já nessa posição."""
    arquivo = dbk_sem_pagamentos()
    gravar(arquivo, *reversed(ITENS))
    assert arquivo.linhas == dbk_do_programa().linhas

    outro_medico = {**MEDICO, "cnpj_cpf": "555.666.777-20"}
    posicao = arquivo.indices("26")[1]                       # o médico do DBK é o 2º pagamento
    gravar(arquivo, outro_medico)
    assert arquivo.indices("26")[2] == posicao + 1
    assert [Registro26.CODIGO.ler(l) for l in arquivo.linhas_do_tipo("26")] == \
           ["01", "10", "10", "15", "26", "30", "36", "70", "99"]


def test_pagamento_ja_no_dbk_vai_para_revisao(caplog):
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, MEDICO, {**MEDICO, "cnpj_cpf": "555.666.777-20"})
    assert resultado.revisao == [1] and resultado.novos == [2]
    assert len(arquivo.linhas) == len(antes) + 1
    assert resultado.dbk_nao_informados == [1, 3, 4, 5, 6, 7, 8]
    assert "mesmo código, tipo e beneficiário" in caplog.text


def test_exterior_e_identificado_pelo_nome():
    resultado = gravar(dbk_do_programa(), EXTERIOR, {**EXTERIOR, "nome": "Outro Doctor"})
    assert resultado.revisao == [1] and resultado.novos == [2]


def test_dependente_fora_do_dbk_vai_para_revisao():
    arquivo = dbk_do_programa()
    antes = list(arquivo.linhas)
    resultado = gravar(arquivo, {**PLANO, "cpf_dependente_alimentando": "444.555.666-19", "cnpj_cpf": "60.701.190/0001-04"})
    assert resultado.sem_vinculado == [1] and arquivo.linhas == antes


def test_relatorio_sem_dados_do_cliente():
    resultado = gravar(dbk_do_programa(), MEDICO, {**PLANO, "cpf_dependente_alimentando": "444.555.666-19"},
                       {**ALUGUEL, "cnpj_cpf": "00.000.000/0001-91"})
    texto = "\n".join(t for _, t in pagamentos.relatorio(resultado))
    assert "1 novo(s), 2 para revisão" in texto
    assert "itens da ficha): 1, 3, 4, 5, 6, 7, 8" in texto
    assert not any(d in texto for d in ("44455566619", "MEDICO", "1500", "LOCADOR"))


# --- main ---

def test_main_grava_pagamentos_com_as_outras_fichas(tmp_path):
    from test_fichas_e_leiaute import rodar_main
    execucao, saida = rodar_main(tmp_path, {"cpf": CPF, "pagamentos": [MEDICO, ALUGUEL]})
    assert execucao.returncode == 0, execucao.stderr
    assert "Pagamentos Efetuados: 2 novo(s), 0 para revisão" in execucao.stderr
    assert ArquivoDBK.ler(saida).linhas_do_tipo("26")[-2:] == [LINHAS[1], LINHAS[6]]
