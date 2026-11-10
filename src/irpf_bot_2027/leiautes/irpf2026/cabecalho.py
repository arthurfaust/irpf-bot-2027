"""
Cabeçalho (registro IR) do arquivo .DBK do IRPF 2026. Somente os campos que o bot lê.

Origem:
    - Posições: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_HEADER" Identificador="IR">: SISTEMA (C8), EXERCICIO (N4), ANO_BASE (N4).

Atenção: o código de controle do cabeçalho NÃO é o CRC32 da linha (algoritmo desconhecido).
Por isso esta classe serve só para leitura; não use linha_vazia nem gravar_cod_controle nela.
"""

from irpf_bot_2027.dbk import ArquivoDBK, Campo, Registro
from irpf_bot_2027.leiautes.irpf2026 import ANO_CALENDARIO, EXERCICIO

class CabecalhoIR(Registro):
    TIPO = "IR"
    TAMANHO = 1244

    SISTEMA   = Campo(1, 8)            # "IRPF    "
    EXERCICIO = Campo(9, 12, "N")      # ano da entrega (ex.: 2026)
    ANO_BASE  = Campo(13, 16, "N")     # ano-calendário (ex.: 2025)

def verificar_exercicio(arquivo: ArquivoDBK) -> str | None:
    """Mensagem de erro se o DBK não for do exercício deste leiaute; None se estiver certo."""
    cabecalhos = arquivo.linhas_do_tipo(CabecalhoIR.TIPO)
    if not cabecalhos:
        return 'o arquivo de entrada não tem o cabeçalho "IR"; não parece um DBK do IRPF'

    exercicio = CabecalhoIR.EXERCICIO.ler(cabecalhos[0])
    ano_base = CabecalhoIR.ANO_BASE.ler(cabecalhos[0])
    if (exercicio, ano_base) != (EXERCICIO, ANO_CALENDARIO):
        return (f'o DBK é do exercício {exercicio} (ano-calendário {ano_base}), mas o bot está usando '
                f'o leiaute do exercício {EXERCICIO} (ano-calendário {ANO_CALENDARIO})')
    return None
