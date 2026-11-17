"""
Leiaute do registro 21 (Rendimentos Tributáveis Recebidos de PJ pelo Titular) do .DBK do IRPF 2026.

Origem:
    - Posições, tamanhos e tipos: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_RENDPJ" Identificador="21">. Os nomes foram simplificados; o original está
      no comentário.
    - Confirmado em DBK gravado pelo programa em 17/11/2026 (tests/dados/rendpj_programa.DBK): CPF da
      fonte pagadora alinhado à esquerda com espaços no campo de 14; data de saída em branco.
    - Código de controle: CRC32 das posições 1 a 160 (dbk.Registro), confirmado nas linhas do programa.
"""

from irpf_bot_2027.dbk import Campo, Registro

class Registro21(Registro):
    TIPO = "21"
    TAMANHO = 170

    TIPO_REGISTRO        = Campo(1, 2, "N")       # NR_REG
    CPF                  = Campo(3, 13)           # NR_CPF: CPF do declarante
    NI_PAGADOR           = Campo(14, 27)          # NR_PAGADOR: CNPJ (ou CPF) da fonte pagadora
    NOME_PAGADOR         = Campo(28, 87)          # NM_PAGADOR
    RENDIMENTOS          = Campo(88, 100, "N", 2)   # VR_RENDTO
    CONTRIBUICAO         = Campo(101, 113, "N", 2)  # VR_CONTRIB: contribuição previdenciária oficial
    DECIMO_TERCEIRO      = Campo(114, 126, "N", 2)  # VR_DECTERC
    IMPOSTO              = Campo(127, 139, "N", 2)  # VR_IMPOSTO: imposto retido na fonte
    DATA_SAIDA           = Campo(140, 147)          # DT_COMUNICACAO_SAIDA (só na declaração de saída)
    IRRF_DECIMO_TERCEIRO = Campo(148, 160, "N", 2)  # VR_IRRF13SALARIO
    CONTROLE             = Campo(161, 170, "N")     # NR_CONTROLE
