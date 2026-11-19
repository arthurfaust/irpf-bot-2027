"""Referência explícita ao item do DBK, o campo "dbk" (docs/adr/0027).

A referência substitui a busca: o item indicado é conferido (existe, é do mesmo tipo e, havendo
identificador forte nos dois lados, é o mesmo) e depois segue a regra de cada ficha para o item
encontrado.
"""

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.exportar import exportar_dbk
from irpf_bot_2027.fichas import FICHAS, alimentandos, bens, dependentes, pagamentos, rendimentos_pj

CPF = "77039677008"


def dbk(nome: str) -> ArquivoDBK:
    return ArquivoDBK.ler(DADOS / nome)


def gravar(ficha, arquivo, *itens):
    campos, erros = ficha.validar(list(itens), CPF)
    assert erros == []
    return ficha.inserir(arquivo, list(itens), campos)


# --- formato ---

@pytest.mark.parametrize(("ficha", "referencia", "valido"), [
    (bens, {"chave": 3}, True), (bens, {"item": 3}, False), (bens, {"chave": "3"}, False),
    (bens, {"chave": 0}, False), (bens, 3, False), (dependentes, {"chave": 1}, True),
    (alimentandos, {"chave": 1}, True), (rendimentos_pj, {"item": 2}, True), (rendimentos_pj, {"chave": 2}, False),
    (pagamentos, {"item": 1}, True), (pagamentos, {"item": True}, False),
])
def test_formato(ficha, referencia, valido):
    nome_dbk = {bens: "contas_programa.DBK", dependentes: "dependentes_programa.DBK",
                alimentandos: "alimentandos_programa.DBK", rendimentos_pj: "rendpj_programa.DBK",
                pagamentos: "pagamentos_programa.DBK"}[ficha]
    item = {**ficha.exportar(dbk(nome_dbk))[0], "dbk": referencia}
    _, erros = ficha.validar([item], CPF)
    assert (erros == []) is valido, erros
    if not valido:
        assert erros == ["%s 1: 'dbk': esperado {\"%s\": N}, com N inteiro a partir de 1" % (
            {"bens": "bem", "rendimentos_pj": "fonte", "pagamentos": "pagamento"}[ficha.CHAVE_JSON],
            "chave" if ficha in (bens, dependentes, alimentandos) else "item")]


# --- o que a busca não resolve e a referência resolve ---

def fundo_no_exterior():
    """O 07/99 do DBK de exterior não tem identificador: a busca manda para revisão (ADR 0018)."""
    arquivo = dbk("exterior_programa.DBK")
    fundo = next(b for b in bens.exportar(arquivo) if (b["grupo"], b["codigo"]) == ("07", "99"))
    return arquivo, {**fundo, "situacao_atual": "99999.00"}


def test_bem_sem_identificador_vai_para_revisao_sem_referencia():
    arquivo, fundo = fundo_no_exterior()
    resultado = gravar(bens, arquivo, {k: v for k, v in fundo.items() if k != "dbk"})
    assert resultado.revisao == [1] and resultado.atualizados == []


def test_bem_sem_identificador_e_atualizado_com_referencia():
    arquivo, fundo = fundo_no_exterior()
    resultado = gravar(bens, arquivo, fundo)
    assert resultado.atualizados == [1] and resultado.por_referencia == [1]
    assert any(l[544:557] == "0000009999900" for l in arquivo.linhas_do_tipo("27"))     # VALOR_ATUAL


def test_pagamento_no_exterior_com_outro_nome_preenche_o_importado():
    """O importado se chama DOCTOR TEST; sem referência, um nome diferente vira lançamento novo."""
    exterior = {"codigo": "15", "tipo": "T", "nome": "Dr Test Clinic", "valor_pago": "3200.00", "pais": "249"}
    sem_ref = gravar(pagamentos, dbk("pagamentos_importados.DBK"), exterior)
    assert sem_ref.novos == [1]
    com_ref = gravar(pagamentos, dbk("pagamentos_importados.DBK"), {**exterior, "dbk": {"item": 3}})
    assert com_ref.preenchidos == [1] and com_ref.por_referencia == [1] and com_ref.novos == []


# --- conferência ---

def test_referencia_inexistente_vai_para_revisao(caplog):
    arquivo, fundo = fundo_no_exterior()
    antes = list(arquivo.linhas)
    resultado = gravar(bens, arquivo, {**fundo, "dbk": {"chave": 999}})
    assert resultado.revisao == [1] and arquivo.linhas == antes
    assert "não existe no DBK" in caplog.text


def test_bem_de_outro_tipo_vai_para_revisao(caplog):
    arquivo, fundo = fundo_no_exterior()
    outro = next(b for b in bens.exportar(arquivo) if (b["grupo"], b["codigo"]) != ("07", "99"))
    resultado = gravar(bens, arquivo, {**fundo, "dbk": outro["dbk"]})
    assert resultado.revisao == [1] and "outro grupo, código ou país" in caplog.text


def test_identificador_forte_diferente_vai_para_revisao(caplog):
    arquivo = dbk("veiculo_programa.DBK")
    _, segundo_carro = [b for b in bens.exportar(arquivo) if (b["grupo"], b["codigo"], b["pais"]) == ("02", "01", "105")]
    renavam_do_primeiro = {**segundo_carro, "veiculo": {"renavam": "12345678900"}}     # indica o 2º com o Renavam do 1º
    resultado = gravar(bens, arquivo, renavam_do_primeiro)
    assert resultado.revisao == [1] and "outro identificador" in caplog.text


def test_duas_referencias_ao_mesmo_item_vao_para_revisao():
    arquivo, fundo = fundo_no_exterior()
    resultado = gravar(bens, arquivo, fundo, {**fundo, "situacao_atual": "1.00"})
    assert resultado.revisao == [1, 2]


def test_item_achado_pela_busca_e_indicado_por_outro_vai_para_revisao(caplog):
    arquivo = dbk("contas_programa.DBK")
    conta = bens.exportar(arquivo)[0]
    resultado = gravar(bens, arquivo, conta, {k: v for k, v in conta.items() if k != "dbk"})
    assert resultado.atualizados == [1] and resultado.revisao == [2]
    assert "indicado em 'dbk' por outro bem" in caplog.text


@pytest.mark.parametrize(("ficha", "nome_dbk", "mudanca", "mensagem"), [
    (dependentes, "dependentes_programa.DBK", {"cpf": "222.333.444-05"}, "outro CPF"),
    (alimentandos, "alimentandos_programa.DBK", {"cpf": "456.456.456-00"}, "outro CPF"),
    (rendimentos_pj, "rendpj_programa.DBK", {"cnpj_cpf": "00.000.000/0001-91"}, "outro CPF/CNPJ"),
    (pagamentos, "pagamentos_programa.DBK", {"cnpj_cpf": "555.666.777-20"}, "outro CPF/CNPJ do beneficiário"),
])
def test_cpf_cnpj_diferente_do_indicado_vai_para_revisao(ficha, nome_dbk, mudanca, mensagem, caplog):
    arquivo = dbk(nome_dbk)
    item = next(i for i in ficha.exportar(arquivo) if set(mudanca) <= set(i) or ficha is not pagamentos)
    if ficha is pagamentos:
        item = next(i for i in ficha.exportar(arquivo) if i["codigo"] == "10")
    resultado = gravar(ficha, arquivo, {**item, **mudanca})
    assert resultado.revisao == [1] and mensagem in caplog.text


# --- ponta a ponta: devolver o JSON exportado não muda o DBK ---

def lancar(arquivo: ArquivoDBK, dados: dict) -> None:
    for ficha in FICHAS:
        itens = dados.get(ficha.CHAVE_JSON, [])
        campos, erros = ficha.validar(itens, CPF)
        assert erros == []
        ficha.inserir(arquivo, itens, campos)


def test_devolver_o_json_exportado_nao_cria_nem_duplica():
    """DBK com todas as fichas (o dados.example.json lançado num DBK sem itens); os DBKs de tests/dados
    têm itens incompletos (o pagamento vazio do DBK vazio, a alimentanda sem processo), que a exportação
    reproduz e a validação recusaria."""
    import json
    from conftest import RAIZ
    base = dbk("entrada.DBK")
    arquivo = ArquivoDBK([l for l in base.linhas if l[:2] not in ("26", "27", "37")], base.quebra_no_fim)
    lancar(arquivo, json.loads((RAIZ / "data" / "dados.example.json").read_text(encoding="utf-8")))
    antes = list(arquivo.linhas)
    dados = exportar_dbk(arquivo)
    assert all(dados[f.CHAVE_JSON] for f in FICHAS)
    for ficha in FICHAS:
        itens = dados[ficha.CHAVE_JSON]
        campos, erros = ficha.validar(itens, CPF)
        assert erros == []
        resultado = ficha.inserir(arquivo, itens, campos)
        assert getattr(resultado, "novos", getattr(resultado, "novas", [])) == []
        assert resultado.por_referencia == list(range(1, len(itens) + 1))
    assert len(arquivo.linhas) == len(antes)
    assert [l[:2] for l in arquivo.linhas] == [l[:2] for l in antes]


def test_relatorio_mostra_os_achados_pela_referencia():
    arquivo, fundo = fundo_no_exterior()
    texto = "\n".join(t for _, t in bens.relatorio(gravar(bens, arquivo, fundo)))
    assert "achados pela referência 'dbk', não pela busca (bens do JSON): 1" in texto
