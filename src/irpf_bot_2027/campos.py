"""
Formato dos campos de largura fixa do arquivo .DBK.

Origem:
    - Tipos "N" (numérico) e "C"/"A" (alfanumérico) e decimais implícitas: 
        - Atributos Tipo e Decimais do irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5).

    - Regras de preenchimento (N com zeros à esquerda; C com espaços à direita; texto em maiúsculas):
        - Não documentadas no leiaute; confirmadas em DBKs gravados pelo programa (tests/dados/).
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

@dataclass(frozen=True)
class Campo:
    ini: int          # posição inicial, contando a partir de 1 (igual ao leiaute)
    fim: int          # posição final, inclusiva
    tipo: str = "C"   # "N" = número (zeros à esquerda) | "C" = texto (espaços à direita)
    decimais: int = 0

    @property
    def tamanho(self) -> int:
        return self.fim - self.ini + 1

    def ler(self, linha: str) -> str:
        return linha[self.ini - 1:self.fim]

    def gravar(self, linha: str, valor) -> str:
        return linha[:self.ini - 1] + self.formatar(valor) + linha[self.fim:]

    def formatar(self, valor) -> str:
        if self.tipo == "N":
            if self.decimais:
                valor = (Decimal(str(valor or 0)) * 10 ** self.decimais).quantize(Decimal(1), ROUND_HALF_UP)  # 1000.00 -> 100000
            texto = str(int(valor or 0)).zfill(self.tamanho)
        else:
            texto = str(valor or "").upper().ljust(self.tamanho)
        if len(texto) != self.tamanho:
            raise ValueError(f"'{valor}' não cabe em {self.tamanho} posições")
        return texto