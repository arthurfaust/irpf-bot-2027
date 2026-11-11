"""Busca de criptoativos (08/01-03) e salvaguarda de chave incompleta (docs/adr/0007)."""

import pytest

from conftest import DADOS
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.fichas.bens.busca import chave_busca, procurar
from irpf_bot_2027.fichas.bens.ficha import montar_linha, proxima_chave
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27

CUSTODIANTE = "11222333000181"
BTC_CUSTODIADO = {
    "grupo": "08", "codigo": "01", "pais": "105", "discriminacao": "BTC na corretora X",
    "situacao_anterior": "1000.00", "situacao_atual": "2000.00", "pertence_a": {"tipo": "T"},
    "cripto": {"autocustodiante": False, "cnpj_custodiante": "11.222.333/0001-81"},
}
BTC_AUTO = {**BTC_CUSTODIADO, "discriminacao": "BTC em carteira propria", "cripto": {"autocustodiante": True}}
ETH = {**BTC_CUSTODIADO, "codigo": "02", "discriminacao": "ETH na corretora X",
       "cripto": {"autocustodiante": False, "cnpj_custodiante": CUSTODIANTE, "altcoin": "eth"}}


def validados(*lista):
    campos, erros = bens.validar(list(lista))
    assert erros == []
    return campos


def gravar(arquivo, *lista):
    return bens.inserir(arquivo, list(lista), validados(*lista))


def dbk_com(bem, cnpj_em_branco=False):
    """entrada.DBK com mais um bem já lançado (como se viesse da declaração anterior)."""
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    [campos] = validados(bem)
    linha = montar_linha(bem, campos, arquivo.cpf_declarante, proxima_chave(arquivo))
    if cnpj_em_branco:                      # declaração antiga, sem o custodiante preenchido
        linha = Registro27.gravar_cod_controle(Registro27.CNPJ_CPF.gravar(linha, ""))
    arquivo.inserir(Registro27.TIPO, linha)
    return arquivo


# --- chave ---

@pytest.mark.parametrize("bem, chave", [
    (BTC_CUSTODIADO, ("08", "01", "", CUSTODIANTE)),
    (BTC_AUTO, ("08", "01", "", "AUTO")),
    (ETH, ("08", "02", "ETH", CUSTODIANTE)),                  # sigla em maiúsculas
], ids=["btc_custodiado", "btc_autocustodiante", "altcoin"])
def test_chave_da_cripto(bem, chave):
    assert chave_busca(validados(bem)[0]) == chave


@pytest.mark.parametrize("bem", [
    {**BTC_CUSTODIADO, "pais": "249", "cripto": {"autocustodiante": False}},      # custodiado no exterior
    {**BTC_CUSTODIADO, "codigo": "10"},                                           # NFT
], ids=["custodiado_no_exterior", "nft"])
def test_cripto_sem_busca(bem):
    assert chave_busca(validados(bem)[0]) is None


# --- 1 encontrado / 0 encontrados ---

def test_btc_autocustodiante_atualiza_o_do_dbk_de_teste():
    """O bitcoin do entrada.DBK (chave 7) é autocustodiante."""
    arquivo = ArquivoDBK.ler(DADOS / "entrada.DBK")
    [posicao] = procurar(arquivo, ("08", "01", "", "AUTO"))
    antes = arquivo.linhas[posicao]

    resultado = gravar(arquivo, {**BTC_AUTO, "situacao_anterior": "1000.00", "situacao_atual": "4321.00"})

    assert resultado.atualizados == [1] and resultado.novos == []
    depois = arquivo.linhas[posicao]
    diferencas = {nome for nome, campo in Registro27.campos().items() if campo.ler(antes) != campo.ler(depois)}
    assert diferencas == {"VALOR_ATUAL", "CONTROLE"}
    assert Registro27.VALOR_ATUAL.ler(depois) == "0000000432100"


def test_altcoin_e_encontrada_pela_sigla_e_pelo_custodiante():
    arquivo = dbk_com(ETH)
    resultado = gravar(arquivo, {**ETH, "cripto": {**ETH["cripto"], "altcoin": "ETH"}, "situacao_atual": "1.00"})
    assert resultado.atualizados == [1]


@pytest.mark.parametrize("outro", [
    {**ETH, "cripto": {**ETH["cripto"], "altcoin": "SOL"}},                        # outro ativo
    {**ETH, "cripto": {**ETH["cripto"], "cnpj_custodiante": "11444777000161"}},    # outro custodiante
    {**ETH, "cripto": {"autocustodiante": True, "altcoin": "ETH"}},                # carteira própria
], ids=["outro_ativo", "outro_custodiante", "autocustodia"])
def test_cripto_diferente_e_lancada_como_nova(outro):
    arquivo = dbk_com(ETH)
    resultado = gravar(arquivo, outro)
    assert resultado.novos == [1] and resultado.atualizados == []


# --- chave incompleta no DBK ---

def test_chave_incompleta_no_dbk_manda_o_bem_do_json_para_revisao(caplog):
    arquivo = dbk_com(BTC_CUSTODIADO, cnpj_em_branco=True)
    antes = list(arquivo.linhas)

    resultado = gravar(arquivo, BTC_CUSTODIADO)

    assert resultado.revisao == [1] and resultado.novos == []
    assert arquivo.linhas == antes
    assert "dados da chave em branco" in caplog.text
    incompletos = [b for b in resultado.nao_informados if b.chave_incompleta]
    assert [(b.grupo, b.codigo) for b in incompletos] == [("08", "01")]
    texto = "\n".join(t for _, t in bens.relatorio(resultado))
    assert "dados da chave em branco no DBK" in texto


def test_chave_incompleta_de_outro_tipo_nao_bloqueia():
    arquivo = dbk_com(ETH, cnpj_em_branco=True)                   # ETH sem custodiante
    resultado = gravar(arquivo, BTC_CUSTODIADO)                    # BTC é outro tipo (08/01)
    assert resultado.novos == [1]
