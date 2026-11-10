"""
Leiaute em uso pelo bot.

O resto do código (main e fichas) importa o leiaute SÓ daqui. Para trocar de ano (ex.: IRPF 2027),
crie leiautes/irpf2027/ com a mesma forma de irpf2026/ e troque "irpf2026" por "irpf2027" nos
imports abaixo. Os testes continuam importando irpf2026 diretamente, porque usam DBKs de 2026.
"""

from irpf_bot_2027.leiautes.irpf2026 import ANO_CALENDARIO, EXERCICIO
from irpf_bot_2027.leiautes.irpf2026.cabecalho import CabecalhoIR, verificar_exercicio
from irpf_bot_2027.leiautes.irpf2026.paises import BRASIL, nome_pais, pais_existe
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27
from irpf_bot_2027.leiautes.irpf2026.regras import (
    SOMENTE_BRASIL, SOMENTE_EXTERIOR, TITULAR_OU_DEPENDENTE, campos_aplicaveis, esta_na_tabela,
)
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import codigo_existe, nome_codigo

__all__ = [
    "ANO_CALENDARIO", "EXERCICIO", "CabecalhoIR", "verificar_exercicio", "Registro27",
    "BRASIL", "nome_pais", "pais_existe",
    "SOMENTE_BRASIL", "SOMENTE_EXTERIOR", "TITULAR_OU_DEPENDENTE", "campos_aplicaveis", "esta_na_tabela",
    "codigo_existe", "nome_codigo",
]
