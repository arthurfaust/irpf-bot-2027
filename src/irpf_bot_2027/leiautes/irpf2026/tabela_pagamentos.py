"""
Códigos e regras da ficha Pagamentos Efetuados (registro 26) do IRPF 2026.

Origem:
    - CODIGOS: lib/resources/tipoPagamentos.xml do programa IRPF2026 (vigência 06/03/2026), coluna COL3.
      Os códigos de doação (40 a 47, 80 e 81) ficam de fora: a tela de pagamentos esconde todos os
      campos com eles (são da ficha Doações Efetuadas).
    - Campos de cada código: PainelPagamentosDetalhe.atualizaGui (classe da tela, lida com javap).
    - Obrigatoriedade e validações: validadores da classe Pagamento (Pagamento$1 a $14, lidos com javap)
      e as mensagens pagamento_* do irpf.jar!/Mensagens.properties.
"""

CODIGOS: dict[str, str] = {
    "01": "Instrução no Brasil",
    "02": "Instrução no exterior",
    "09": "Fonoaudiólogos no Brasil",
    "10": "Médicos no Brasil",
    "11": "Dentistas no Brasil",
    "12": "Psicólogos no Brasil",
    "13": "Fisioterapeutas no Brasil",
    "14": "Terapeutas ocupacionais no Brasil",
    "15": "Médicos no exterior",
    "16": "Dentistas no exterior",
    "17": "Psicólogos no exterior",
    "18": "Fisioterapeutas no exterior",
    "19": "Terapeutas ocupacionais no exterior",
    "20": "Fonoaudiólogos no exterior",
    "21": "Hospitais, clínicas e laboratórios no Brasil",
    "22": "Hospitais, clínicas e laboratórios no exterior",
    "26": "Planos de saúde no Brasil",
    "30": "Pensão judicial paga a residente no Brasil",
    "31": "Pensão judicial paga a não residente",
    "33": "Pensão por escritura pública paga a residente",
    "34": "Pensão por escritura pública paga a não residente",
    "36": "Previdência complementar (inclusive FAPI)",
    "37": "Previdência complementar fechada ou aberta pública",
    "60": "Advogados (exceto de ações trabalhistas)",
    "61": "Advogados (relativos a ações trabalhistas)",
    "62": "Advogados (demais honorários)",
    "66": "Engenheiros, arquitetos e outros autônomos",
    "70": "Aluguéis de imóveis",
    "71": "Administrador de imóveis",
    "72": "Corretor de imóveis",
    "76": "Arrendamento rural",
    "99": "Outros pagamentos",
}

# Pagamento.isPagamentoExterior: país obrigatório (Pagamento$14) e sem CPF/CNPJ na tela.
EXTERIOR = {"02", "15", "16", "17", "18", "19", "20", "22", "31", "34"}

# Pensão alimentícia: sem a pergunta do tipo; o beneficiário é o alimentando escolhido na lista
# (o programa grava o CPF e o nome dele e o tipo "A").
PENSAO = {"30", "31", "33", "34"}

# Tipo do pagamento (titular, dependente ou alimentando) por código (atualizaGui; Pagamento$12 exige
# a resposta nos códigos que têm a pergunta). Código fora do dicionário: sem a pergunta.
TIPOS: dict[str, set[str]] = {
    **{c: {"T", "D", "A"} for c in ("01", "02", "09", "10", "11", "12", "13", "14", "15", "16", "17",
                                    "18", "19", "20", "21", "22", "26")},
    **{c: {"T", "D"} for c in ("36", "37", "99")},
}

# CPF/CNPJ do beneficiário (Pagamento$7, erro quando falta ou é inválido).
CPF_OBRIGATORIO = {"09", "10", "11", "12", "13", "14", "66"}
CNPJ_OBRIGATORIO = {"01", "21", "26", "36", "37"}
NI_OBRIGATORIO = {"60", "61", "62", "70", "71", "72", "76"}      # CPF ou CNPJ
NI_OPCIONAL = {"99"}                                             # em branco: aviso

# Parcela não dedutível/valor reembolsado aparece na tela (atualizaGui) e não pode passar do valor pago
# (Pagamento$8, erro).
COM_PARCELA_NAO_DEDUTIVEL = {"01", "02", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18",
                             "19", "20", "21", "22", "26", "30", "31", "33", "34", "36"}

# Descrição obrigatória (Pagamento$13). Nos demais códigos é opcional.
DESCRICAO_OBRIGATORIA = {"99"}

def codigo_existe(codigo: str) -> bool:
    return codigo in CODIGOS

def nome_codigo(codigo: str) -> str:
    return CODIGOS[codigo]
