"""
Cabeçalho (registro IR) do arquivo .DBK do IRPF 2026. Somente os campos que o bot lê.

Origem:
    - Posições: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_HEADER" Identificador="IR">: SISTEMA (C8), EXERCICIO (N4), ANO_BASE (N4).

Atenção: o código de controle do cabeçalho NÃO é o CRC32 da linha (algoritmo desconhecido).
Por isso esta classe serve só para leitura; não use linha_vazia nem gravar_cod_controle nela.
"""

from irpf_bot_2027.dbk import Campo, Registro

class CabecalhoIR(Registro):
    TIPO = "IR"
    TAMANHO = 1244

    SISTEMA   = Campo(1, 8)            # "IRPF    "
    EXERCICIO = Campo(9, 12, "N")      # ano da entrega (ex.: 2026)
    ANO_BASE  = Campo(13, 16, "N")     # ano-calendário (ex.: 2025)
