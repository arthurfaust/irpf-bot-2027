"""
Grupos e códigos da ficha Bens e Direitos (IRPF 2026).

Gerado a partir de lib/resources/tipoBens.xml do programa IRPF2026 (vigência 05/03/2026).
"""

GRUPOS: dict[str, dict] = {
    "01": {
        "nome": "Bens Imóveis",
        "codigos": {
            "01": "Prédio residencial",
            "02": "Prédio comercial",
            "03": "Galpão",
            "11": "Apartamento",
            "12": "Casa",
            "13": "Terreno",
            "14": "Imóvel rural",
            "15": "Sala ou conjunto",
            "16": "Construção",
            "17": "Benfeitorias até 1988",
            "18": "Loja",
            "19": "Garagem Avulsa",
            "99": "Outros bens imóveis",
        },
    },
    "02": {
        "nome": "Bens Móveis",
        "codigos": {
            "01": "Veículo automotor terrestre: caminhão, automóvel, moto etc",
            "02": "Aeronave",
            "03": "Embarcação",
            "04": "Bem relacionado com o exercício da atividade autônoma",
            "05": "Quadro, objeto de arte, de coleção, antiguidade etc",
            "06": "Joia",
            "99": "Outros bens móveis",
        },
    },
    "03": {
        "nome": "Participações Societárias",
        "codigos": {
            "01": "Ações (inclusive as listadas em bolsa)",
            "02": "Quotas ou quinhões de capital",
            "03": "Holding Patrimonial - ações ou quotas adquiridas por integralização de bens (já declarados) ao capital",
            "99": "Outras participações societárias",
        },
    },
    "04": {
        "nome": "Aplicações e Investimentos",
        "codigos": {
            "01": "Depósito em conta poupança",
            "02": "Títulos públicos e privados sujeitos à tributação (Tesouro Direto, CDB, RDB e Outros)",
            "03": "Títulos isentos de tributação (LCI, LCA, LCD, CRI, CRA, LIG, Debêntures de Infraestrutura e outros)",
            "04": "Ativos negociados em bolsa no Brasil (BDRs, opções e outros - exceto ações e fundos)",
            "05": "Ouro, ativo financeiro",
            "99": "Outras aplicações e investimentos",
        },
    },
    "05": {
        "nome": "Créditos",
        "codigos": {
            "01": "Empréstimos concedidos",
            "02": "Crédito decorrente de alienação",
            "99": "Outros créditos",
        },
    },
    "06": {
        "nome": "Depósito à Vista e Numerário",
        "codigos": {
            "01": "Depósito em conta corrente ou conta pagamento",
            "02": "Conta gráfica mantida em agente operador de loterias de apostas de quota fixa - Lei 14.790/2023",
            "10": "Dinheiro em espécie - moeda nacional",
            "11": "Dinheiro em espécie - moeda estrangeira",
            "99": "Outros depósitos à vista",
        },
    },
    "07": {
        "nome": "Fundos",
        "codigos": {
            "01": "Fundos de Investimentos sujeitos à tributação periódica (come-cotas) - Lei 14.754/2023",
            "02": "Fundos de Investimento nas Cadeias Produtivas Agroindustriais (Fiagro) - Lei 8.668/1993",
            "03": "Fundos de Investimento Imobiliário (FII) - Lei 8.668/1993",
            "04": "Fundos de Investimento em Ações (Lei 14.754/2023) e Fundos Mútuos de Privatização - FGTS (Lei 8.036/1990)",
            "06": "FIP - Entidade de investimento, FIDC - Entidade de investimento sem tributação periódica (come-cotas), ETF - Entidade de investimento - Lei 14.754/2023",
            "07": "Fundos de Investimento em Participações em Infraestrutura (FIP-IE) e Fundos de Investimento em Participação na Produção Econômica Intensiva em Pesquisa, Desenvolvimento e Inovação (FIP-PD&I) - Lei 11.478/2007",
            "08": "Fundos de Índice de Renda Fixa (ETFs) - Lei 13.043/2014, art. 2º",
            "10": "Fundos de Infraestrutura, FIDC e outros Fundos de Investimento (alíquota 0%) - Lei 12.431/2011 arts. 2º e 3º",
            "12": "Fundos de Investimentos em Empresas Emergente - FIEE Lei 11.312/2006, art 2º",
            "13": "Fundo multimercado Lei 14.754/2023, art. 25 combinado com o art. 40",
            "99": "Fundos de Investimento no Exterior - Lei 14.754/2023, arts. 2º a 14",
        },
    },
    "08": {
        "nome": "Criptoativos",
        "codigos": {
            "01": "Criptoativo Bitcoin - BTC",
            "02": "Outras criptomoedas, conhecidas como altcoins, por exemplo, Ether (ETH), Ripple (XRP), Bitcoin Cash (BCH) e Litecoin (LTC)",
            "03": "Criptoativos conhecidos como stablecoins, por exemplo, Tether (USDT), USD Coin (USDC), Brazilian Digital Token (BRZ), Binance USD (BUSD), DAI, True USD (TUSD), Gemini USD (GUSD, Paxos USD (PAX), Paxos Gold (PAXG), etc",
            "10": "Criptoativos conhecidos como NFTs (Non-Fungible Tokens)",
            "99": "Outros criptoativos",
        },
    },
    "99": {
        "nome": "Outros Bens e Direitos",
        "codigos": {
            "01": "Licença e concessão especiais",
            "02": "Título de clube e assemelhado",
            "03": "Direito de autor, de inventor e patente",
            "04": "Direito de lavra e assemelhado",
            "05": "Consórcio não contemplado",
            "06": "VGBL - Vida Gerador de Benefício Livre",
            "07": "Juros Sobre Capital Próprio a receber",
            "08": "Leasing com opção de compra a ser exercida no final do contrato",
            "99": "Outros bens e direitos",
        },
    },
}


def nome_grupo(grupo: str) -> str:
    return GRUPOS[grupo]["nome"]


def nome_codigo(grupo: str, codigo: str) -> str:
    return GRUPOS[grupo]["codigos"][codigo]


def codigo_existe(grupo: str, codigo: str) -> bool:
    return codigo in GRUPOS.get(grupo, {}).get("codigos", {})
