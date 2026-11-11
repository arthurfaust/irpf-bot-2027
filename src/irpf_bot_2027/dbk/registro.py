"""
Classe-base dos registros (linhas) do arquivo .DBK.

Cada tipo de registro (27 = bem, 37 = aplicações no exterior...) é uma subclasse que define
TIPO, TAMANHO e um atributo Campo para cada posição do leiaute, inclusive CONTROLE.

Origem:
    - Código de controle: CRC32 (zlib) de tudo o que vem antes do campo CONTROLE (os últimos
      10 caracteres da linha), em decimal com 10 dígitos.
        - Não documentado no leiaute; confirmado em todas as linhas (exceto o cabeçalho IR)
          dos DBKs gravados pelo programa (tests/dados/).
"""

import zlib

from irpf_bot_2027.dbk.campo import Campo

class Registro:
    TIPO: str = ""
    TAMANHO: int = 0
    CONTROLE: Campo

    @classmethod
    def campos(cls) -> dict[str, Campo]:
        """Campos do registro, na ordem da linha."""
        campos = {nome: valor for nome, valor in vars(cls).items() if isinstance(valor, Campo)}
        return dict(sorted(campos.items(), key=lambda item: item[1].ini))

    @classmethod
    def ler_tudo(cls, linha: str) -> dict[str, str]:
        """Texto de cada campo da linha, por nome: "C"/"A" sem os espaços à direita; "N" como está
        (com zeros à esquerda e decimais implícitas), para não perder zeros de códigos como "07"."""
        if len(linha) != cls.TAMANHO or not linha.startswith(cls.TIPO):
            raise ValueError(f"a linha não é um registro {cls.TIPO} de {cls.TAMANHO} posições")
        return {nome: campo.ler(linha) if campo.tipo == "N" else campo.ler(linha).rstrip()
                for nome, campo in cls.campos().items()}

    @classmethod
    def linha_vazia(cls) -> str:
        """Linha do tamanho do registro: campos numéricos com zeros, o resto com espaços."""
        linha = " " * cls.TAMANHO
        for campo in cls.campos().values():
            if campo.tipo == "N":
                linha = campo.gravar(linha, 0)
        return linha

    @classmethod
    def gravar_cod_controle(cls, linha: str) -> str:
        """Grava o código de controle. Deve ser sempre a última alteração da linha."""
        corpo = linha[:cls.CONTROLE.ini - 1]
        return cls.CONTROLE.gravar(linha, zlib.crc32(corpo.encode("latin-1")))
