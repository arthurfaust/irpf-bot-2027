"""
Converte um bem do JSON do cliente em campos do Registro27.

Os campos do primeiro nível (grupo, codigo, discriminacao...) estão em CAMPOS_SIMPLES, e cada
bloco (pertence_a, cripto, imovel) tem uma tabela em MAPA_BLOCOS que diz para qual campo do
Registro27 vai cada chave. CONVERSOES traduz o formato amigável do JSON (true/false, "m2"/"ha")
para o código que o DBK espera. Chave desconhecida e obrigatório ausente viram erro.

Origem dos códigos gravados:
    - Do irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5), descrição dos campos do registro 27:
        - UNIDADE_AREA (NM_UNID):                0 = m², 1 = ha, 2 = vazio
        - REGISTRADO_CARTORIO (NM_IND_REG_IMOV): 0 = não, 1 = sim, 2 = vazio
        - AUTOCUSTODIANTE (IN_CUSTODIANTE):      0 = não, 1 = sim
        - TITULAR_DEPENDENTE (IN_TIPO_BENEFIC):  "T" titular, "D" dependente

    - Confirmados em DBKs gravados pelo programa (tests/dados/):
        - DATA_AQUISICAO (DT_AQUISICAO): DDMMAAAA 
            - O leiaute não informa o formato;
            - Confirmado em 10/11/2026 com a data 23/10/2020 gravada como "23102020".
        - CNPJ_CPF, CPF_DONO, CEP: somente dígitos.

    - Chaves e blocos do JSON: 
        - Formato definido por este projeto (não vem do programa).
"""

import logging

from functools import partial

from irpf_bot_2027.comum.conversoes import data_ddmmaaaa, numero, sim_nao, so_digitos, titular_dependente, valor_em_reais

logger = logging.getLogger(__name__)

# JSON -> campo do Registro27: campos do primeiro nível do bem
CAMPOS_SIMPLES = {
    "grupo": "GRUPO",
    "codigo": "CODIGO",
    "pais": "PAIS",
    "discriminacao": "DISCRIMINACAO",
    "situacao_anterior": "VALOR_ANTERIOR",          # situação em 31/12 do ano anterior
    "situacao_atual": "VALOR_ATUAL",                # situação em 31/12 do ano-calendário
    "usufruto": "USUFRUTO",                         # true | false (opcional, padrão false)
}

# Campos do primeiro nível que todo bem precisa ter (o programa exige grupo, código, país e discriminação;
# os dois valores são exigidos aqui para a IA não omitir um valor por engano: use "0.00" quando for zero).
CAMPOS_OBRIGATORIOS = ("grupo", "codigo", "pais", "discriminacao", "situacao_anterior", "situacao_atual")

# JSON -> campo do Registro27: blocos
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
ORIGEM_NO_JSON = {
    **{campo: chave for chave, campo in CAMPOS_SIMPLES.items()},
    **{campo: f"{bloco}.{chave}" for bloco, mapa in MAPA_BLOCOS.items() for chave, campo in mapa.items()},
}

# Campos que existem no mapa mas ainda não podem ser gravados, com o motivo.
CAMPOS_BLOQUEADOS: dict[str, str] = {}

# JSON -> código do DBK (as conversões genéricas ficam em comum/conversoes.py)
def unidade_area(valor) -> int:
    unidades = {"m2": 0, "ha": 1}
    if valor not in unidades:
        raise ValueError(f'esperado "m2" ou "ha", veio {valor!r}')
    return unidades[valor]

def codigo_pais(valor) -> str:
    """"105", 105 ou "13" -> código de 3 dígitos ("105", "013"). A existência é conferida na validação."""
    texto = str(valor).strip()
    if isinstance(valor, bool) or not texto.isdigit() or len(texto) > 3:
        raise ValueError('esperado o código do país com até 3 dígitos (ex.: "105" para o Brasil)')
    return texto.zfill(3)

CONVERSOES = {
    "PAIS": codigo_pais,
    "VALOR_ANTERIOR": valor_em_reais,
    "VALOR_ATUAL": valor_em_reais,
    "AREA": partial(numero, casas=1),               # área com 1 casa decimal (N11,1 no leiaute)
    "USUFRUTO": sim_nao,
    "TITULAR_DEPENDENTE": titular_dependente,
    "CPF_DONO": so_digitos,
    "AUTOCUSTODIANTE": sim_nao,
    "CNPJ_CPF": so_digitos,
    "CEP": so_digitos,
    "UNIDADE_AREA": unidade_area,
    "REGISTRADO_CARTORIO": sim_nao,
    "DATA_AQUISICAO": data_ddmmaaaa,
}

# main func
def converter_campos(bem: dict) -> tuple[dict, list[str]]:
    """
    Lê os blocos do bem e devolve ({campo_do_registro: valor_convertido}, [erros]).
    Args:
        bem (dict): Dicionário com os dados do bem
    Returns:
        tuple[dict, list[str]]: Tupla contendo:
            - Dicionários com os campos
            - Lista de erros encontrados.
    Os erros são acumulados (não para no primeiro) para que o usuário veja tudo de uma vez.
    Trata os campos do primeiro nível (CAMPOS_SIMPLES) e os blocos (MAPA_BLOCOS).
    """
    campos = {}
    erros = []

    def converter(origem: str, nome: str, valor) -> None:
        if nome in CAMPOS_BLOQUEADOS:
            erros.append(f"'{origem}': {CAMPOS_BLOQUEADOS[nome]}")
            return
        conversao = CONVERSOES.get(nome)
        try:
            campos[nome] = conversao(valor) if conversao else valor
        except ValueError as erro:
            erros.append(f"'{origem}': {erro}")

    for chave, conteudo in bem.items():
        if not isinstance(conteudo, dict):
            if chave in CAMPOS_SIMPLES:
                converter(chave, CAMPOS_SIMPLES[chave], conteudo)
            else:
                erros.append(f"campo desconhecido '{chave}'")
            continue

        if chave not in MAPA_BLOCOS:
            erros.append(f"bloco desconhecido '{chave}'")
            continue

        mapa = MAPA_BLOCOS[chave]
        for subchave, valor in conteudo.items():
            if subchave in mapa:
                converter(f"{chave}.{subchave}", mapa[subchave], valor)
            else:
                erros.append(f"campo desconhecido '{chave}.{subchave}'")

    for chave in CAMPOS_OBRIGATORIOS:
        if bem.get(chave) is None or str(bem[chave]).strip() == "":
            erros.append(f"campo obrigatório '{chave}' não informado")

    logger.debug("Campos lidos: %s", sorted(campos))
    return campos, erros
