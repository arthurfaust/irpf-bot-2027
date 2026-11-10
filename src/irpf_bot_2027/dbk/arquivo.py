"""
Leitura, busca, inserção e gravação de linhas no arquivo .DBK.

Não sabe nada de fichas: trabalha só com linhas e tipos de registro (os 2 primeiros caracteres).

Origem:
    - Encoding Latin-1 e fim de linha CRLF, sem CRLF depois da última linha (T9): confirmados em
      DBKs gravados pelo programa (tests/dados/).
    - ORDEM_REGISTROS: ordem dos <Registro> no bloco <DeclaracaoTXT TipoArquivo="ARQ_IRPF"> do
      irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5). Os DBKs do programa seguem
      essa ordem (IR, 16, 19, 20, 26, 27, 37, T9).
"""

from pathlib import Path

ENCODING = "latin-1"
FIM_DE_LINHA = "\r\n"
CABECALHO = "IR"

ORDEM_REGISTROS = (
    "SR", "IP", "IR",
    "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "45", "46", "47", "48", "49", "50", "51",
    "52", "53", "54", "55", "56", "57", "58", "59",
    "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93", "94", "95", "96",
    "97", "98", "99",
    "T9", "HR", "DR", "R9",
    "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76",
)

def tipo_da_linha(linha: str) -> str:
    return linha[:2]

class ArquivoDBK:
    def __init__(self, linhas: list[str], quebra_no_fim: bool = False):
        self.linhas = linhas                    # sem o fim de linha
        self.quebra_no_fim = quebra_no_fim      # o DBK do programa NÃO tem CRLF depois da última linha

    @classmethod
    def ler(cls, caminho: Path) -> "ArquivoDBK":
        linhas = caminho.read_bytes().decode(ENCODING).split(FIM_DE_LINHA)
        quebra_no_fim = bool(linhas) and linhas[-1] == ""
        if quebra_no_fim:
            linhas.pop()
        return cls(linhas, quebra_no_fim)

    def gravar(self, caminho: Path) -> None:
        texto = FIM_DE_LINHA.join(self.linhas) + (FIM_DE_LINHA if self.quebra_no_fim else "")
        caminho.write_bytes(texto.encode(ENCODING))

    def indices(self, tipo: str) -> list[int]:
        """Posições (a partir de 0) das linhas de um tipo de registro."""
        return [i for i, linha in enumerate(self.linhas) if tipo_da_linha(linha) == tipo]

    def linhas_do_tipo(self, tipo: str) -> list[str]:
        return [self.linhas[i] for i in self.indices(tipo)]

    @property
    def cpf_declarante(self) -> str:
        """CPF das posições 3-13, comum a todas as linhas exceto o cabeçalho."""
        linha = next(l for l in self.linhas if tipo_da_linha(l) != CABECALHO)
        return linha[2:13]

    def posicao_para(self, tipo: str) -> int:
        """Onde uma nova linha do tipo deve entrar: depois da última do mesmo tipo ou,
        se não houver nenhuma, antes da primeira linha de um tipo que venha depois na ORDEM_REGISTROS."""
        existentes = self.indices(tipo)
        if existentes:
            return existentes[-1] + 1

        ordem = ORDEM_REGISTROS.index(tipo)
        for i, linha in enumerate(self.linhas):
            outro = tipo_da_linha(linha)
            if outro in ORDEM_REGISTROS and ORDEM_REGISTROS.index(outro) > ordem:
                return i
        return len(self.linhas)

    def inserir(self, tipo: str, linha: str) -> int:
        """Insere a linha na posição certa e devolve a posição (a partir de 0)."""
        posicao = self.posicao_para(tipo)
        self.linhas.insert(posicao, linha)
        return posicao
