"""Converte os blocos do JSON do cliente em campos do Registro27.

Cada bloco do JSON (pertence_a, cripto, imovel) tem uma tabela em MAPA_BLOCOS que diz
para qual campo do Registro27 vai cada chave. CONVERSOES traduz o formato amigável do
JSON (true/false, "m2"/"ha") para o código que o DBK espera.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- de-para: bloco do JSON -> campo do Registro27

MAPA_BLOCOS = {
    "pertence_a": {
        "tipo": "TITULAR_DEPENDENTE",               # "T" titular | "D" dependente
        "cpf": "CPF_DONO",                          # CPF do dependente (quando tipo = "D")
    },
    "cripto": {
        "autocustodiante": "AUTOCUSTODIANTE",
        "cnpj_custodiante": "CNPJ_CPF",
        "altcoin": "ALTCOIN",                       # só código 02 (ex.: "ETH")
        "stablecoin": "STABLECOIN",                 # só código 03 (ex.: "USDT")
    },
    "imovel": {
        "logradouro": "LOGRADOURO",
        "numero": "NUMERO",
        "complemento": "COMPLEMENTO",
        "bairro": "BAIRRO",
        "cep": "CEP",
        "uf": "UF",
        "cod_municipio": "COD_MUNICIPIO",
        "municipio": "MUNICIPIO",
        "area": "AREA",
        "unidade": "UNIDADE_AREA",                  # "m2" | "ha"
        "data_aquisicao": "DATA_AQUISICAO",         # "AAAA-MM-DD" no JSON -> DDMMAAAA no DBK
        "iptu": "IPTU",
        "cib": "CIB",                               # imóvel rural (código 14)
        "cei_cno": "CEI_CNO",                       # construção (código 16)
        "registrado_cartorio": "REGISTRADO_CARTORIO",
        "matricula": "MATRICULA",
        "cartorio": "CARTORIO",
    },
}

# Caminho no JSON de cada campo do Registro27, para as mensagens de erro (ex.: "CNPJ_CPF" -> "cripto.cnpj_custodiante").
ORIGEM_NO_JSON = {campo: f"{bloco}.{chave}" for bloco, mapa in MAPA_BLOCOS.items() for chave, campo in mapa.items()}

# Campos que existem no mapa mas ainda não podem ser gravados, com o motivo.
CAMPOS_BLOQUEADOS: dict[str, str] = {}


# ---------------------------------------------------------------- conversões: formato do JSON -> código do DBK

def sim_nao(valor) -> int:
    if not isinstance(valor, bool):
        raise ValueError(f"esperado true ou false, veio {valor!r}")
    return 1 if valor else 0


def so_digitos(valor) -> str:
    return "".join(ch for ch in str(valor) if ch.isdigit())


def titular_dependente(valor) -> str:
    valor = str(valor).upper()
    if valor not in ("T", "D"):
        raise ValueError(f'esperado "T" ou "D", veio {valor!r}')
    return valor


def unidade_area(valor) -> int:
    unidades = {"m2": 0, "ha": 1}
    if valor not in unidades:
        raise ValueError(f'esperado "m2" ou "ha", veio {valor!r}')
    return unidades[valor]


def data_ddmmaaaa(valor) -> str:
    """"2020-10-23" -> "23102020". Formato confirmado numa cópia de segurança gerada pelo programa."""
    try:
        data = date.fromisoformat(str(valor))
    except ValueError:
        raise ValueError(f'esperada data no formato "AAAA-MM-DD", veio {valor!r}') from None
    return data.strftime("%d%m%Y")


CONVERSOES = {
    "TITULAR_DEPENDENTE": titular_dependente,
    "CPF_DONO": so_digitos,
    "AUTOCUSTODIANTE": sim_nao,
    "CNPJ_CPF": so_digitos,
    "CEP": so_digitos,
    "UNIDADE_AREA": unidade_area,
    "REGISTRADO_CARTORIO": sim_nao,
    "DATA_AQUISICAO": data_ddmmaaaa,
}


# ---------------------------------------------------------------- função principal

def campos_do_bem(bem: dict) -> tuple[dict, list[str]]:
    """Lê os blocos do bem e devolve ({campo_do_registro: valor_convertido}, [erros]).

    Os erros são acumulados (não para no primeiro) para que o usuário veja tudo de uma vez.
    Chaves fora dos blocos (grupo, codigo, pais, discriminacao...) não são tratadas aqui.
    """
    campos = {}
    erros = []

    for bloco, conteudo in bem.items():
        if not isinstance(conteudo, dict):
            continue                                # campos simples do bem, tratados no main
        if bloco not in MAPA_BLOCOS:
            erros.append(f"bloco desconhecido '{bloco}'")
            continue

        mapa = MAPA_BLOCOS[bloco]
        for chave, valor in conteudo.items():
            if chave not in mapa:
                erros.append(f"campo desconhecido '{bloco}.{chave}'")
                continue

            nome = mapa[chave]
            if nome in CAMPOS_BLOQUEADOS:
                erros.append(f"'{bloco}.{chave}': {CAMPOS_BLOQUEADOS[nome]}")
                continue

            converter = CONVERSOES.get(nome)
            try:
                campos[nome] = converter(valor) if converter else valor
            except ValueError as erro:
                erros.append(f"'{bloco}.{chave}': {erro}")

    logger.debug("Campos extras lidos: %s", sorted(campos))
    return campos, erros
