"""
Regras da tela "Editar: Bem e Direito" do IRPF 2026.

Dizem quais campos do Registro27 aparecem na tela para cada grupo, código e país.

Origem:
    - Extraídas das classes do programa IRPF2026 (versão 1.5), lidas com javap:
        - lib-modulos/irpf-negocio-declaracao.jar!/serpro/ppgd/irpf/negocio/bens/Bem.class (19/05/2026)
        - lib-modulos/irpf-gui-declaracao.jar!/serpro/ppgd/irpf/gui/declaracao/bens/PainelBensDetalhe.class (13/04/2026)

    Tabela                         | Método de origem
     ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
    TEM_CNPJ_CPF                   | Bem.isBemComNI / Bem.tituloCampoNI
    CRIPTO_COM_CUSTODIANTE         | Bem.isCriptoativos + PainelBensDetalhe.habilitarCamposCriptoativos
    CONTA_BANCARIA                 | Bem.isBemComDadosBancarios + PainelBensDetalhe.habilitarCampoBanco
    NEGOCIADO_EM_BOLSA             | Bem.isBemNegociadoBolsa + PainelBensDetalhe.habilitaCampoCodigoNegociacao
    TITULAR_OU_DEPENDENTE          | Bem.isBemComBeneficiario
    APLICACAO_FINANCEIRA_EXTERIOR  | Bem.isBemComAplicacaoFinanceira
    LUCROS_DIVIDENDOS_EXTERIOR     | Bem.isBemComLucrosDividendos
    REGISTRO_BEM_MOVEL             | Bem.isBemRegistravel / Bem.tituloCampoRegistro
    REGISTRO_IMOVEL                | Bem.tituloCampoRegistro / Bem.tamanhoCampoRegistro
    campos_imovel (cartório, data) | Bem.isBemImovelRegistravel + PainelBensDetalhe.habilitarCampoDataAquisicao, habilitaCampoBemImovelRegistrado

    Conferidas com a Ajuda do programa (help/AjudaIRPF.pdf, capítulo "Bens e Direitos", págs. 178 a 234) e com a tela do programa nos bens de teste.

    Atenção: estas regras estão no código do programa, não em um arquivo de dados. A cada nova versão do IRPF, refazer a extração e conferir.

Cada tabela abaixo segue o formato de tabela_bens.py:
    
grupo -> códigos em que a regra vale (TODOS = todos os códigos do grupo).
"""

TODOS = "todos"
BRASIL = "105"

CAMPOS_COMUNS = {"GRUPO", "CODIGO", "PAIS", "DISCRIMINACAO", "VALOR_ANTERIOR", "VALOR_ATUAL", "USUFRUTO"}

# CNPJ/CPF (só no Brasil). A cripto tem regra própria: CRIPTO_COM_CUSTODIANTE.
TEM_CNPJ_CPF = {
    "03": TODOS,                                    # Participações societárias
    "04": {"01", "02", "03", "99"},                 # Poupança, títulos tributados, títulos isentos, outras aplicações
    "05": TODOS,                                    # Créditos (CPF/CNPJ do devedor)
    "06": {"01", "02", "99"},                       # Conta corrente, conta em operador de apostas, outros depósitos
    "07": {"01", "02", "03", "04", "06", "07",      # Todos os fundos, exceto 99 (fundo no exterior)
           "08", "10", "12", "13"},
    "99": {"05", "06", "07"},                       # Consórcio, VGBL, JCP a receber
}

# Pergunta "É autocustodiante?". Se a resposta for Não, aparece o "CNPJ Custodiante".
CRIPTO_COM_CUSTODIANTE = {
    "08": {"01", "02", "03", "10"},                 # Bitcoin, altcoins, stablecoins, NFTs
}

# Banco, agência, conta e DV (só no Brasil).
CONTA_BANCARIA = {
    "04": {"01"},                                   # Depósito em conta poupança
    "06": {"01"},                                   # Depósito em conta corrente ou conta pagamento
}

# Pergunta "Negociados em Bolsa?" (no Brasil ou no exterior).
NEGOCIADO_EM_BOLSA = {
    "03": {"01"},                                   # Ações
    "04": {"04"},                                   # Ativos negociados em bolsa (BDRs, opções...)
    "07": {"02", "03", "04", "06", "07", "08",      # Fiagro, FII, FIA, FIP/FIDC/ETF, FIP-IE, ETF renda fixa,
           "10", "12", "13", "99"},                 # infraestrutura, FIEE, multimercado, fundo no exterior
}

# Pergunta "Bem ou direito pertencente ao: Titular / Dependente".
TITULAR_OU_DEPENDENTE = {
    "03": TODOS, "04": TODOS, "05": TODOS, "06": TODOS, "07": TODOS, "08": TODOS,
    "99": {"05", "06", "07", "08", "99"},           # Consórcio, VGBL, JCP, leasing, outros
}

# Quadro "Aplicação Financeira" (Lei 14.754 - só no exterior).
APLICACAO_FINANCEIRA_EXTERIOR = {
    "03": TODOS,
    "04": {"02", "05", "99"},                       # Títulos tributados, ouro, outras aplicações
    "05": TODOS,
    "06": {"01", "99"},                             # Conta corrente, outros depósitos
    "07": {"99"},                                   # Fundo no exterior
    "08": TODOS,
    "99": {"06", "07", "08", "99"},                 # VGBL, JCP, leasing, outros
}

# Quadro "Lucros e Dividendos" (Lei 14.754 - só no exterior). Igual ao anterior, sem o grupo 06.
LUCROS_DIVIDENDOS_EXTERIOR = {g: c for g, c in APLICACAO_FINANCEIRA_EXTERIOR.items() if g != "06"}

# Campo único de registro dos bens móveis (no Brasil ou no exterior).
REGISTRO_BEM_MOVEL = {
    "01": "RENAVAM",                                # Veículo (no exterior a tela chama de "Registro de Veículo")
    "02": "REG_AERONAVE",                           # Aeronave
    "03": "REG_EMBARCACAO",                         # Embarcação
}

# Campo único de registro dos imóveis (só no Brasil). Os demais códigos usam IPTU.
REGISTRO_IMOVEL = {
    "14": "CIB",                                    # Imóvel rural
    "16": "CEI_CNO",                                # Construção
    "17": None,                                     # Benfeitorias: não tem registro
}

ENDERECO_IMOVEL = {"LOGRADOURO", "NUMERO", "COMPLEMENTO", "BAIRRO", "CEP", "MUNICIPIO", "AREA", "UNIDADE_AREA"}
SEM_DATA_NEM_CARTORIO = {"16", "17"}                # Construção e benfeitorias

def esta_na_tabela(tabela: dict, grupo: str, codigo: str) -> bool:
    """True se o par grupo/código aparece na tabela (TODOS vale para qualquer código)."""
    codigos = tabela.get(grupo)
    return codigos == TODOS or (codigos is not None and codigo in codigos)


def campos_imovel(codigo: str, no_brasil: bool) -> set[str]:
    campos = set(ENDERECO_IMOVEL)
    if no_brasil:
        campos |= {"UF", "COD_MUNICIPIO"}
        registro = REGISTRO_IMOVEL.get(codigo, "IPTU")
        if registro:
            campos.add(registro)
    if codigo not in SEM_DATA_NEM_CARTORIO:
        campos.add("DATA_AQUISICAO")
        if no_brasil:
            campos |= {"REGISTRADO_CARTORIO", "MATRICULA", "CARTORIO"}
    return campos

def tem_cnpj_cpf(grupo: str, codigo: str, no_brasil: bool, autocustodiante: bool) -> bool:
    if not no_brasil:
        return False
    if esta_na_tabela(CRIPTO_COM_CUSTODIANTE, grupo, codigo):
        return not autocustodiante
    return esta_na_tabela(TEM_CNPJ_CPF, grupo, codigo)

def campos_cripto(grupo: str, codigo: str) -> set[str]:
    campos = set()
    if esta_na_tabela(CRIPTO_COM_CUSTODIANTE, grupo, codigo):
        campos.add("AUTOCUSTODIANTE")
    if (grupo, codigo) == ("08", "02"):
        campos.add("ALTCOIN")
    if (grupo, codigo) == ("08", "03"):
        campos.add("STABLECOIN")
    return campos

# Função principal
def campos_aplicaveis(g: str, c: str, pais: str, autocustodiante: bool = False, bolsa: bool = False) -> set[str]:
    """
    Campos do Registro27 aplicáveis ao bem.
    Args:
        g,c: Grupo e código com 2 dígitos ("08", "01")
        pais: Código do país ("105" = Brasil)
        autocustodiante: Resposta a "É autocustodiante?" (só cripto)
        bolsa: Resposta a "Negociados em Bolsa?"
    Returns:
        set[str]: Coleção com os campos aplicáveis
    """
    no_brasil = pais == BRASIL
    campos = set(CAMPOS_COMUNS)

    if g == "01":
        campos |= campos_imovel(c, no_brasil)

    if g == "02" and c in REGISTRO_BEM_MOVEL:
        campos.add(REGISTRO_BEM_MOVEL[c])

    if tem_cnpj_cpf(g, c, no_brasil, autocustodiante):
        campos.add("CNPJ_CPF")

    if no_brasil and esta_na_tabela(CONTA_BANCARIA, g, c):
        campos |= {"BANCO", "AGENCIA", "CONTA", "DV_CONTA"}
        if g == "06":
            campos.add("CONTA_PAGAMENTO")

    if esta_na_tabela(NEGOCIADO_EM_BOLSA, g, c):
        campos.add("BOLSA")
        if bolsa:
            campos.add("COD_NEGOCIACAO")

    campos |= campos_cripto(g, c)

    if esta_na_tabela(TITULAR_OU_DEPENDENTE, g, c):
        campos |= {"TITULAR_DEPENDENTE", "CPF_DONO"}

    if not no_brasil and esta_na_tabela(APLICACAO_FINANCEIRA_EXTERIOR, g, c):
        campos |= {"AF_RENDIMENTO", "AF_IMPOSTO"}

    if not no_brasil and esta_na_tabela(LUCROS_DIVIDENDOS_EXTERIOR, g, c):
        campos |= {"LD_RECEBIDO", "LD_IMPOSTO"}

    return campos