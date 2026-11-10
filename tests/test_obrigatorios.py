"""Campos obrigatórios por tipo de bem."""

import json

import pytest

from conftest import DADOS
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.regras import campos_aplicaveis, campos_obrigatorios
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import GRUPOS

BITCOIN, APARTAMENTO = json.loads((DADOS / "bens.json").read_text(encoding="utf-8"))["bens"]
BASE = {"pais": "105", "discriminacao": "Teste", "situacao_anterior": "0.00", "situacao_atual": "100.00"}


def sem_no_bloco(bem: dict, bloco: str, chave: str) -> dict:
    return {**bem, bloco: {k: v for k, v in bem[bloco].items() if k != chave}}


@pytest.mark.parametrize("pais", ["105", "111"])
@pytest.mark.parametrize("autocustodiante", [False, True])
@pytest.mark.parametrize("registrado", [False, True])
def test_obrigatorios_sao_sempre_campos_que_aparecem_na_tela(pais, autocustodiante, registrado):
    """Um campo obrigatório que não aparece na tela seria impossível de preencher."""
    for grupo, dados in GRUPOS.items():
        for codigo in dados["codigos"]:
            obrigatorios = campos_obrigatorios(grupo, codigo, pais, autocustodiante, registrado, dependente=True)
            aplicaveis = campos_aplicaveis(grupo, codigo, pais, autocustodiante)
            assert obrigatorios <= aplicaveis, (grupo, codigo, obrigatorios - aplicaveis)


@pytest.mark.parametrize(
    "chave", ["logradouro", "cep", "uf", "cod_municipio", "municipio", "area", "unidade", "data_aquisicao",
              "registrado_cartorio"],
)
def test_imovel_no_brasil_sem_campo_obrigatorio(chave):
    _, erros = validar_bem(sem_no_bloco(APARTAMENTO, "imovel", chave))
    assert erros == [f"'imovel.{chave}' é obrigatório para 01/11 (Apartamento) no Brasil"]


@pytest.mark.parametrize("chave", ["matricula", "cartorio"])
def test_imovel_registrado_exige_matricula_e_cartorio(chave):
    _, erros = validar_bem(sem_no_bloco(APARTAMENTO, "imovel", chave))
    assert erros == [f"'imovel.{chave}' é obrigatório para 01/11 (Apartamento) no Brasil"]


def test_imovel_nao_registrado_dispensa_matricula_e_cartorio():
    imovel = {k: v for k, v in APARTAMENTO["imovel"].items() if k not in ("matricula", "cartorio")}
    _, erros = validar_bem({**APARTAMENTO, "imovel": {**imovel, "registrado_cartorio": False}})
    assert erros == []


def test_construcao_dispensa_data_e_cartorio():
    imovel = {"logradouro": "Rua X", "cep": "80000000", "uf": "PR", "cod_municipio": "7535",
              "municipio": "Curitiba", "area": "50.0", "unidade": "m2"}
    _, erros = validar_bem({**BASE, "grupo": "01", "codigo": "16", "imovel": imovel})
    assert erros == []


def test_imovel_no_exterior_exige_so_logradouro_area_e_unidade():
    _, erros = validar_bem({**BASE, "grupo": "01", "codigo": "11", "pais": "111",
                            "imovel": {"logradouro": "Rua X", "area": "50.0", "unidade": "m2",
                                       "data_aquisicao": "2020-01-01"}})
    assert erros == []


def test_bitcoin_com_custodiante_exige_cnpj():
    _, erros = validar_bem({**BITCOIN, "cripto": {"autocustodiante": False}})
    assert erros == ["'cripto.cnpj_custodiante' é obrigatório para 08/01 (Criptoativo Bitcoin - BTC) no Brasil"]


def test_bitcoin_autocustodiante_dispensa_cnpj():
    _, erros = validar_bem({**BITCOIN, "cripto": {"autocustodiante": True}})
    assert erros == []


def test_cripto_exige_a_resposta_de_autocustodiante():
    _, erros = validar_bem({k: v for k, v in BITCOIN.items() if k != "cripto"})
    assert "'cripto.autocustodiante' é obrigatório para 08/01 (Criptoativo Bitcoin - BTC) no Brasil" in erros


def test_altcoin_exige_o_codigo_da_moeda():
    _, erros = validar_bem({**BASE, "grupo": "08", "codigo": "02", "cripto": {"autocustodiante": True}})
    assert erros == ["'cripto.altcoin' é obrigatório para 08/02 (Outras criptomoedas, conhecidas como altcoins, "
                     "por exemplo, Ether (ETH), Ripple (XRP), Bitcoin Cash (BCH) e Litecoin (LTC)) no Brasil"]


def test_dependente_exige_cpf():
    _, erros = validar_bem({**BITCOIN, "pertence_a": {"tipo": "D"}})
    assert erros == ["'pertence_a.cpf' é obrigatório para 08/01 (Criptoativo Bitcoin - BTC) no Brasil"]


def test_titular_dispensa_cpf():
    _, erros = validar_bem({**BITCOIN, "pertence_a": {"tipo": "T"}})
    assert erros == []


def test_acoes_no_brasil_exigem_cnpj():
    _, erros = validar_bem({**BASE, "grupo": "03", "codigo": "01"})
    assert erros == ["'cnpj_cpf' é obrigatório para 03/01 (Ações (inclusive as listadas em bolsa)) no Brasil"]


def test_acoes_com_cnpj_sao_aceitas():
    campos, erros = validar_bem({**BASE, "grupo": "03", "codigo": "01", "cnpj_cpf": "33.000.167/0001-01"})
    assert erros == []
    assert campos["CNPJ_CPF"] == "33000167000101"


def test_cripto_tambem_aceita_o_cnpj_pelo_primeiro_nivel():
    bem = {**BITCOIN, "cripto": {"autocustodiante": False}, "cnpj_cpf": "12345678000199"}
    _, erros = validar_bem(bem)
    assert erros == []


def test_cnpj_informado_duas_vezes_e_barrado():
    _, erros = validar_bem({**BITCOIN, "cnpj_cpf": "12345678000199"})      # o bloco cripto vem antes no JSON
    assert erros == ["'cripto.cnpj_custodiante' e 'cnpj_cpf' informam o mesmo campo; use só um deles"]


def test_cnpj_em_bem_que_nao_tem_cnpj_cita_o_caminho_usado():
    _, erros = validar_bem({**APARTAMENTO, "cnpj_cpf": "12345678000199"})
    assert erros == ["'cnpj_cpf' não se aplica a 01/11 (Apartamento) no Brasil"]


def test_acoes_no_exterior_dispensam_cnpj():
    _, erros = validar_bem({**BASE, "grupo": "03", "codigo": "01", "pais": "111"})
    assert erros == []


@pytest.mark.parametrize(
    ("grupo", "codigo", "campo"),
    [("06", "01", "AGENCIA"), ("04", "01", "AGENCIA"), ("02", "01", "RENAVAM"), ("02", "03", "REG_EMBARCACAO")],
    ids=["conta-corrente", "poupanca", "veiculo", "embarcacao"],
)
def test_bens_que_exigem_campos_ainda_nao_suportados(grupo, codigo, campo):
    bem = {**BASE, "grupo": grupo, "codigo": codigo}
    if grupo in ("04", "06"):
        bem["cnpj_cpf"] = "00000000000191"
    _, erros = validar_bem(bem)
    assert any(f"exige o campo {campo}, que ainda não pode ser informado no JSON" in erro for erro in erros), erros
