"""
Leiaute do registro 35 (Alimentandos) do .DBK do IRPF 2026. Por enquanto só é lido (para ligar
pagamentos ao alimentando pela chave).

Origem:
    - Posições, tamanhos e tipos: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_ALIMENTANDO" Identificador="35">. Nome original no comentário.
    - Confirmado em DBK gravado pelo programa em 18/11/2026 (tests/dados/pagamentos_programa.DBK).
"""

from irpf_bot_2027.dbk import Campo, Registro

class Registro35(Registro):
    TIPO = "35"
    TAMANHO = 331

    TIPO_REGISTRO        = Campo(1, 2, "N")         # NR_REG
    CPF                  = Campo(3, 13)             # NR_CPF: CPF do declarante
    RESIDENCIA           = Campo(14, 14, "N")       # INDICADOR_RESIDENC: 0 = Brasil
    CHAVE                = Campo(15, 19, "N")       # NR_CHAVE
    NOME                 = Campo(20, 79)            # NM_NOME
    DATA_NASCIMENTO      = Campo(80, 87, "N")       # DT_NASCIM (DDMMAAAA)
    CPF_ALIMENTANDO      = Campo(88, 98)            # NI_ALIMENTANDO
    CPF_VINCULADO        = Campo(99, 109)           # NR_CPF_VINCULADO
    TIPO_PROCESSO        = Campo(110, 110)          # IN_TIPO_PROCESSO
    PROCESSO_JUDICIAL    = Campo(111, 135)          # NR_PROCESSOJUDICIAL
    VARA_CIVIL           = Campo(136, 139)          # NR_IDENTIFICACAOVARACIVIL
    COMARCA              = Campo(140, 169)          # NM_COMARCA
    DATA_DECISAO         = Campo(170, 177)          # DT_DECJUDICIAL
    UF_COMARCA           = Campo(178, 179)          # SG_UFCOMARCA
    CNPJ_CARTORIO        = Campo(180, 193)          # NR_CNPJ_CARTORIO
    NOME_CARTORIO        = Campo(194, 253)          # NM_CARTORIO
    DATA_LAVRATURA       = Campo(254, 261)          # DT_LAVRATURA
    LIVRO                = Campo(262, 268)          # NM_LIVRO
    FOLHA                = Campo(269, 275)          # NM_FOLHA
    COD_MUNICIPIO        = Campo(276, 279, "N")     # CD_MUNICIP
    MUNICIPIO            = Campo(280, 319)          # NM_MUNICIPIO
    UF_CARTORIO          = Campo(320, 321)          # SG_UFCARTORIO
    CONTROLE             = Campo(322, 331, "N")     # NR_CONTROLE
