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
        - Bloco conta (DBK gravado pelo programa em 13/11/2026, tests/manual/contas/): banco com 3
          dígitos, agência com zeros à esquerda ("1" -> "0001"), conta como digitada (exceto na Caixa,
          veja ajustar_conta_caixa), DV alinhado à esquerda ("X"), IN_CONTA_PAGAMENTO 0/1.
        - Bloco bolsa (DBK gravado pelo programa em 16/11/2026, tests/dados/bolsa_programa.DBK):
          IN_BOLSA 1 = sim, 0 = não (descrição do campo no mapeamentoTxt.xml); código de negociação em
          maiúsculas, em branco quando não é negociado; código com 13 caracteres aceito.
        - Bloco veiculo (DBK gravado pelo programa em 16/11/2026, tests/dados/veiculo_programa.DBK):
          Renavam e registro estrangeiro do veículo em NR_RENAVAN (veja ajustar_registro_veiculo);
          registros de aeronave e embarcação como digitados (com hífen).
        - Bloco exterior (DBK gravado pelo programa em 17/11/2026, tests/dados/exterior_programa.DBK):
          prejuízo gravado com "-" na primeira posição (-250,00 = "-000000025000"). As linhas 24
          (rendimento exclusivo, código 13) e 37 (demonstrativo) são calculadas pelo programa.

    - Chaves e blocos do JSON: 
        - Formato definido por este projeto (não vem do programa).
"""

import logging

from functools import partial

from irpf_bot_2027.comum.conversoes import data_ddmmaaaa, numero, sim_nao, so_digitos, titular_dependente, valor_em_reais
from irpf_bot_2027.leiautes.atual import CAIXA, Registro27

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
    "cnpj_cpf": "CNPJ_CPF",                         # CNPJ da empresa, instituição ou fundo; CPF/CNPJ do devedor
                                                    # nos créditos (grupo 05). Na cripto use cripto.cnpj_custodiante.
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
    "conta": {                                      # poupança (04/01) e conta corrente/pagamento (06/01)
        "banco": "BANCO",                           # código com até 3 dígitos (ex.: "001"), da tabela do programa
        "agencia": "AGENCIA",                       # até 4 dígitos, sem o dígito da agência
        "conta": "CONTA",                           # só os números, sem o dígito verificador
        "dv": "DV_CONTA",                           # dígito verificador da conta (1 ou 2 caracteres, ex.: "X")
        "conta_pagamento": "CONTA_PAGAMENTO",       # true | false (só 06/01, opcional, padrão false)
    },
    "bolsa": {                                      # ações, BDRs/opções (04/04) e fundos com a pergunta
        "negociado": "BOLSA",                       # true | false: "Negociados em Bolsa?" (obrigatório onde aparece)
        "codigo": "COD_NEGOCIACAO",                 # código de negociação (ex.: "PETR4"), obrigatório se negociado
    },
    "veiculo": {                                    # bens móveis registráveis (grupo 02)
        "renavam": "RENAVAM",                       # 02/01: Renavam no Brasil (9 ou 11 dígitos); no exterior,
                                                    # o registro do veículo no país (a tela chama de "Registro de Veículo")
        "registro_aeronave": "REG_AERONAVE",        # 02/02
        "registro_embarcacao": "REG_EMBARCACAO",    # 02/03
    },
    "exterior": {                                   # bens no exterior: valores do ano (Lei 14.754/2023)
        "lucro_prejuizo": "AF_RENDIMENTO",          # aplicação financeira: lucro, ou prejuízo com "-" (ex.: "-250.00")
        "imposto_pago": "AF_IMPOSTO",               # imposto pago no exterior sobre a aplicação
        "dividendos_recebidos": "LD_RECEBIDO",      # lucros e dividendos recebidos
        "imposto_dividendos": "LD_IMPOSTO",         # imposto pago no exterior sobre lucros e dividendos
    },
}

# Caminhos no JSON de cada campo do Registro27, para as mensagens de erro. Um campo pode ter mais de um
# (ex.: CNPJ_CPF vem de "cnpj_cpf" ou de "cripto.cnpj_custodiante").
ORIGENS_NO_JSON: dict[str, list[str]] = {}
for _chave, _campo in CAMPOS_SIMPLES.items():
    ORIGENS_NO_JSON.setdefault(_campo, []).append(_chave)
for _bloco, _mapa in MAPA_BLOCOS.items():
    for _chave, _campo in _mapa.items():
        ORIGENS_NO_JSON.setdefault(_campo, []).append(f"{_bloco}.{_chave}")

def informado_no_json(bem: dict, origem: str) -> bool:
    """True se o caminho ("situacao_atual" ou "imovel.area") tem algum valor no bem do JSON."""
    valor = bem
    for parte in origem.split("."):
        valor = valor.get(parte) if isinstance(valor, dict) else None
    return valor is not None

def origem_no_json(bem: dict, campo: str) -> str | None:
    """Caminho no JSON de onde o campo veio (ou deveria vir, se não foi informado). None se não há caminho."""
    caminhos = ORIGENS_NO_JSON.get(campo)
    if not caminhos:
        return None
    for caminho in caminhos:
        if informado_no_json(bem, caminho):
            return caminho
    if campo == "CNPJ_CPF" and bem.get("grupo") == "08":
        return "cripto.cnpj_custodiante"
    return caminhos[0]

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

def so_numeros(valor, maximo: int, formato: str, dica: str = "") -> str:
    """Texto só com dígitos, com até `maximo` dígitos. A mensagem não repete o valor (dado do cliente)."""
    texto = str(valor).strip()
    if isinstance(valor, bool) or not isinstance(valor, (str, int)) or not texto.isdigit():
        raise ValueError(f"esperado {formato}, só com números{dica}")
    if len(texto) > maximo:
        raise ValueError(f"esperado {formato}, com até {maximo} dígitos")
    return texto

def codigo_banco(valor) -> str:
    """"1", 1 ou "001" -> "001". A existência na tabela do programa é conferida na validação."""
    return so_numeros(valor, 3, 'o código do banco (ex.: "001")').zfill(3)

def agencia(valor) -> str:
    return so_numeros(valor, 4, "o número da agência", dica=", sem o dígito da agência")

def numero_conta(valor) -> str:
    return so_numeros(valor, Registro27.CONTA.tamanho, "o número da conta",
                      dica="; o dígito verificador vai em 'conta.dv'")

def digito_conta(valor) -> str:
    texto = str(valor).strip()
    if isinstance(valor, bool) or not isinstance(valor, (str, int)) or not texto.isalnum() \
            or len(texto) > Registro27.DV_CONTA.tamanho:
        raise ValueError('esperado o dígito verificador com 1 ou 2 letras ou números (ex.: "7" ou "X")')
    return texto

# Tamanho do campo "Código de Negociação" na tela (Bem.codigoNegociacao, Alfa de 13); o DBK tem 20.
TAMANHO_COD_NEGOCIACAO = 13

def codigo_negociacao(valor) -> str:
    """"petr4" -> "PETR4". Só letras e números, até 13 caracteres (o limite da tela)."""
    texto = str(valor).strip().upper()
    if isinstance(valor, bool) or not isinstance(valor, str) or not texto.isalnum() or not texto.isascii():
        raise ValueError('esperado o código de negociação só com letras e números (ex.: "PETR4")')
    if len(texto) > TAMANHO_COD_NEGOCIACAO:
        raise ValueError(f"o código de negociação tem no máximo {TAMANHO_COD_NEGOCIACAO} caracteres")
    return texto

def texto_de_registro(valor) -> str:
    """Registro de veículo, aeronave ou embarcação: texto (o tamanho é conferido na validação)."""
    if isinstance(valor, bool) or not isinstance(valor, (str, int)) or not str(valor).strip():
        raise ValueError("esperado o número do registro como texto")
    return str(valor).strip()

def ajustar_registro_veiculo(campos: dict) -> None:
    """Veículo (02/01), no Brasil ou no exterior: registro com menos de 11 caracteres ganha zeros à
    esquerda até 11, como o programa grava.

    Origem: observador Bem$11 do IRPF 2026 (registro de 02/01 com 1 a 10 caracteres é completado com
    zeros à esquerda até 11) e DBK gravado pelo programa em 16/11/2026: Renavam 987654322 gravado como
    00987654322 e o registro estrangeiro ABC1234-FL como 0ABC1234-FL.
    """
    if (campos.get("GRUPO"), campos.get("CODIGO")) == ("02", "01") and "RENAVAM" in campos:
        campos["RENAVAM"] = campos["RENAVAM"].rjust(11, "0")

def ajustar_conta_caixa(campos: dict, erros: list[str]) -> None:
    """Conta da Caixa: completa com zeros à esquerda até 12 dígitos, como o programa grava.

    Origem: Bem.getContaFormatadaTxt do IRPF 2026 (banco 104 sem operação = conta com 12 dígitos) e
    DBK gravado pelo programa em 13/11/2026 (conta 4321 gravada como 000000004321). A tela de bens não
    tem o campo Operação; quem tem conta antiga com operação informa operação + conta no campo conta.
    """
    if campos.get("BANCO") != CAIXA or "CONTA" not in campos:
        return
    if len(campos["CONTA"]) > 12:
        erros.append("'conta.conta': na Caixa (banco 104) a conta tem no máximo 12 dígitos")
        del campos["CONTA"]
        return
    campos["CONTA"] = campos["CONTA"].zfill(12)

CONVERSOES = {
    "PAIS": codigo_pais,
    "BANCO": codigo_banco,
    "AGENCIA": agencia,
    "CONTA": numero_conta,
    "DV_CONTA": digito_conta,
    "CONTA_PAGAMENTO": sim_nao,
    "BOLSA": sim_nao,
    "COD_NEGOCIACAO": codigo_negociacao,
    "AF_RENDIMENTO": partial(numero, casas=2, permite_negativo=True),   # Bem.lucroPrejuizo é Valor (aceita negativo)
    "AF_IMPOSTO": valor_em_reais,                                       # os outros três são ValorPositivo
    "LD_RECEBIDO": valor_em_reais,
    "LD_IMPOSTO": valor_em_reais,
    "RENAVAM": texto_de_registro,
    "REG_AERONAVE": texto_de_registro,
    "REG_EMBARCACAO": texto_de_registro,
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
    origem_usada = {}                               # campo -> caminho do JSON que o preencheu

    def converter(origem: str, nome: str, valor) -> None:
        if nome in origem_usada:
            erros.append(f"'{origem_usada[nome]}' e '{origem}' informam o mesmo campo; use só um deles")
            return
        origem_usada[nome] = origem
        if nome in CAMPOS_BLOQUEADOS:
            erros.append(f"'{origem}': {CAMPOS_BLOQUEADOS[nome]}")
            return
        conversao = CONVERSOES.get(nome)
        try:
            campos[nome] = conversao(valor) if conversao else valor
        except ValueError as erro:
            erros.append(f"'{origem}': {erro}")

    for chave, conteudo in bem.items():
        if chave in ("dbk", "origem"):              # campos de controle (docs/adr/0027 e 0028): validados em ficha.validar
            continue
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

    ajustar_conta_caixa(campos, erros)
    ajustar_registro_veiculo(campos)

    for chave in CAMPOS_OBRIGATORIOS:
        if bem.get(chave) is None or str(bem[chave]).strip() == "":
            erros.append(f"campo obrigatório '{chave}' não informado")

    logger.debug("Campos lidos: %s", sorted(campos))
    return campos, erros
