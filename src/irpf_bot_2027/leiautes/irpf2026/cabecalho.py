"""
Cabeçalho (registro IR) do arquivo .DBK do IRPF 2026. Somente os campos que o bot lê.

Origem:
    - Posições: irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5),
      <Registro Nome="REG_HEADER" Identificador="IR">: SISTEMA (C8), EXERCICIO (N4), ANO_BASE (N4).

    - Código de controle (NR_CONTROLE, posições 1235-1244): classes DocumentoAjusteTXT
      (atualizaHeader, preparaNomeArquivoParaCrc) e RegistroTxt (calculaCRCHeader), lidas com javap.
      É o CRC32 do NOME DO ARQUIVO seguido da linha sem os 10 últimos caracteres; ver controle_cabecalho.
      Confirmado nos DBKs de tests/dados/.

Atenção: o controle do cabeçalho NÃO é o CRC32 só da linha. Por isso esta classe serve só para
leitura; não use linha_vazia nem gravar_cod_controle nela. Na restauração de um .DBK o programa
calcula esse controle mas não o compara (DocumentoAjusteTXT.validarHeader só confere o CPF e
SISTEMA = "IRPF"), então um DBK renomeado continua sendo aceito.
"""

import zlib
from pathlib import PurePath

from irpf_bot_2027.dbk import ArquivoDBK, Campo, Registro
from irpf_bot_2027.leiautes.irpf2026 import ANO_CALENDARIO, EXERCICIO

class CabecalhoIR(Registro):
    TIPO = "IR"
    TAMANHO = 1244

    SISTEMA   = Campo(1, 8)            # "IRPF    "
    EXERCICIO = Campo(9, 12, "N")      # ano da entrega (ex.: 2026)
    ANO_BASE  = Campo(13, 16, "N")     # ano-calendário (ex.: 2025)

def controle_cabecalho(linha: str, nome_arquivo: str) -> str:
    """Código de controle do cabeçalho IR como o programa calcula ao gravar o arquivo.

    Prefixo = nome do arquivo em maiúsculas: até 8 caracteres do nome sem extensão + a extensão com
    ponto (ex.: "77039677008-IRPF-A-2026-2025-ORIGI.DBK" -> "77039677.DBK").
    Não reproduz UtilitariosString.retiraCaracteresEspeciais, que o programa aplica à linha antes
    do CRC; vale para cabeçalhos só com caracteres comuns (o caso dos DBKs de teste).
    """
    caminho = PurePath(nome_arquivo.upper())
    prefixo = caminho.stem[:8] + caminho.suffix
    corpo = linha[:CabecalhoIR.TAMANHO - 10]
    return str(zlib.crc32((prefixo + corpo).encode("latin-1"))).zfill(10)

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
