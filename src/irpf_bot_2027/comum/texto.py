"""
Normalização de texto antes de gravar no .DBK.

O DBK é gravado em Latin-1 (ISO-8859-1), uma linha por registro. Textos vindos de IA ou de
documentos costumam trazer caracteres fora do Latin-1 (aspas curvas, travessões, reticências) e
quebras de linha, que quebrariam o registro em duas linhas.

normalizar_texto troca os casos comuns por equivalentes aceitos. O que sobrar fora do Latin-1
é barrado na validação, com a indicação do caractere.

Origem:
    - Encoding Latin-1 e uma linha por registro: confirmados em DBKs gravados pelo programa (tests/dados/).
    - A tabela de trocas é uma escolha deste projeto (não vem do programa).
"""

import re
import unicodedata

TROCAS = {
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',   # “ ” „ « »
    "‘": "'", "’": "'", "‚": "'", "´": "'", "`": "'",       # ‘ ’ ‚ ´ `
    "–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-",   # – — − ‐ ‑
    "…": "...",                                                              # …
    "•": "-", "·": "-",                                                 # • ·
    " ": " ", " ": " ", " ": " ",                                  # espaços especiais
}
QUEBRAS_E_TABULACOES = re.compile(r"[\r\n\t]+")
ESPACOS_REPETIDOS = re.compile(r" {2,}")

def normalizar_texto(texto: str) -> str:
    """Deixa o texto pronto para o DBK: troca caracteres comuns fora do Latin-1, junta as linhas
    e remove espaços repetidos e nas pontas."""
    texto = unicodedata.normalize("NFC", texto)          # "a" + acento separado -> "á"
    for original, troca in TROCAS.items():
        texto = texto.replace(original, troca)
    texto = QUEBRAS_E_TABULACOES.sub(" ", texto)
    texto = ESPACOS_REPETIDOS.sub(" ", texto)
    return texto.strip()

def caracteres_fora_do_latin1(texto: str) -> list[str]:
    """Caracteres do texto que o DBK não consegue gravar, sem repetir, na ordem em que aparecem."""
    vistos = []
    for caractere in texto:
        if ord(caractere) > 0xFF and caractere not in vistos:
            vistos.append(caractere)
    return vistos
