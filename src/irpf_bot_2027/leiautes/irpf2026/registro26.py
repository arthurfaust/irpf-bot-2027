"""
Leiaute do registro 26 (Pagamentos Efetuados) do .DBK do IRPF 2026.

Origem:
    - Posições, tamanhos e tipos: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_PAGAMENTO" Identificador="26">. Os nomes foram simplificados; o original está
      no comentário.
    - Confirmado em DBK gravado pelo programa em 18/11/2026 (tests/dados/pagamentos_programa.DBK):
        - CPF do beneficiário alinhado à esquerda com espaços no campo de 14;
        - TIPO_NI: 1 = CPF, 2 = CNPJ, 0 = sem CPF/CNPJ;
        - TIPO_PAGAMENTO: "T", "D" ou "A"; em branco nos códigos sem a pergunta (advogados, profissionais
          liberais, aluguéis, arrendamento); "A" na pensão alimentícia;
        - CHAVE_DEPENDENTE: chave do dependente (registro 25) ou do alimentando (registro 35); 0 no titular;
        - PAIS: 000 nos pagamentos no Brasil.
    - Código de controle: CRC32 das posições 1 a 661 (dbk.Registro), confirmado nas linhas do programa.
"""

from irpf_bot_2027.dbk import Campo, Registro

class Registro26(Registro):
    TIPO = "26"
    TAMANHO = 671

    TIPO_REGISTRO        = Campo(1, 2, "N")         # NR_REG
    CPF                  = Campo(3, 13)             # NR_CPF: CPF do declarante
    CODIGO               = Campo(14, 15, "N")       # CD_PAGTO
    CHAVE_DEPENDENTE     = Campo(16, 20, "N")       # NR_CHAVE_DEPEND: dependente ou alimentando
    NI_BENEFICIARIO      = Campo(21, 34)            # NR_BENEF: CPF/CNPJ do beneficiário
    NOME_BENEFICIARIO    = Campo(35, 94)            # NM_BENEF
    NIT                  = Campo(95, 105)           # NR_NIT: empregado doméstico (código 50, fora da tabela de 2026)
    VALOR_PAGO           = Campo(106, 118, "N", 2)  # VR_PAGTO
    PARCELA_NAO_DEDUTIVEL = Campo(119, 131, "N", 2) # VR_REDUC: parcela não dedutível ou reembolsada
    CONTRIB_PATROCINADOR = Campo(132, 144, "N", 2)  # VR_CONTRIB_PATR: contribuição do ente público patrocinador
    TIPO_NI              = Campo(145, 145, "N")     # IN_TIPO_CPF_CNPJ
    TIPO_PAGAMENTO       = Campo(146, 146)          # IN_TIPO_PGTO: T, D ou A
    DESCRICAO            = Campo(147, 658)          # NM_DESCRICAO
    PAIS                 = Campo(659, 661, "N")     # CD_PAIS
    CONTROLE             = Campo(662, 671, "N")     # NR_CONTROLE
