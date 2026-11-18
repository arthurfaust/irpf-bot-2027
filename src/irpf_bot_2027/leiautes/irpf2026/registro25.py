"""
Leiaute do registro 25 (Dependentes) do .DBK do IRPF 2026. Por enquanto só é lido (para ligar
pagamentos ao dependente pela chave).

Origem:
    - Posições, tamanhos e tipos: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_DEPENDENTE" Identificador="25">. Nome original no comentário.
    - Confirmado em DBK gravado pelo programa em 18/11/2026 (tests/dados/pagamentos_programa.DBK).
"""

from irpf_bot_2027.dbk import Campo, Registro

class Registro25(Registro):
    TIPO = "25"
    TAMANHO = 224

    TIPO_REGISTRO        = Campo(1, 2, "N")         # NR_REG
    CPF                  = Campo(3, 13)             # NR_CPF: CPF do declarante
    CHAVE                = Campo(14, 18, "N")       # NR_CHAVE
    CODIGO               = Campo(19, 20)            # CD_DEPEND: relação de dependência
    NOME                 = Campo(21, 80)            # NM_DEPEND
    DATA_NASCIMENTO      = Campo(81, 88, "N")       # DT_NASCIM (DDMMAAAA)
    CPF_DEPENDENTE       = Campo(89, 99)            # NI_DEPEND
    SAIDA                = Campo(100, 100)          # IN_SAIDA
    NIT                  = Campo(101, 111)          # NR_NITPISPASEP
    MORA_COM_TITULAR     = Campo(112, 112)          # IN_ENDERECO_TITULAR
    EMAIL                = Campo(113, 202)          # NM_EMAIL
    DDD_CELULAR          = Campo(203, 204)          # NR_DDD_CELULAR
    CELULAR              = Campo(205, 213)          # NR_CELULAR
    RACA_COR             = Campo(214, 214, "N")     # IN_RACA_COR
    CONTROLE             = Campo(215, 224, "N")     # NR_CONTROLE
