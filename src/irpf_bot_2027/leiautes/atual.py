"""
Leiaute em uso pelo bot.

O resto do código (main e fichas) importa o leiaute SÓ daqui. Para trocar de ano (ex.: IRPF 2027),
crie leiautes/irpf2027/ com a mesma forma de irpf2026/ e troque "irpf2026" por "irpf2027" nos
imports abaixo. Os testes continuam importando irpf2026 diretamente, porque usam DBKs de 2026.
"""

from irpf_bot_2027.leiautes.irpf2026 import ANO_CALENDARIO, EXERCICIO
from irpf_bot_2027.leiautes.irpf2026.bancos import CAIXA, banco_existe, nome_banco
from irpf_bot_2027.leiautes.irpf2026.cabecalho import CabecalhoIR, controle_cabecalho, verificar_exercicio
from irpf_bot_2027.leiautes.irpf2026.nome_pessoa import erro_nome_pessoa
from irpf_bot_2027.leiautes.irpf2026.paises import BRASIL, nome_pais, pais_existe
from irpf_bot_2027.leiautes.irpf2026 import tabela_dependentes, tabela_pagamentos
from irpf_bot_2027.leiautes.irpf2026.registro21 import Registro21
from irpf_bot_2027.leiautes.irpf2026.registro25 import Registro25
from irpf_bot_2027.leiautes.irpf2026.registro26 import Registro26
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27
from irpf_bot_2027.leiautes.irpf2026.registro35 import Registro35
from irpf_bot_2027.leiautes.irpf2026.regras import (
    CNPJ_OBRIGATORIO, CONTA_BANCARIA, REGISTRO_BEM_MOVEL, REGISTRO_IMOVEL, SOMENTE_BRASIL, SOMENTE_EXTERIOR,
    TITULAR_OU_DEPENDENTE, campos_aplicaveis, campos_obrigatorios,
    esta_na_tabela, renavam_valido, tem_cnpj_cpf,
)
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import codigo_existe, nome_codigo

__all__ = [
    "ANO_CALENDARIO", "EXERCICIO", "CabecalhoIR", "controle_cabecalho", "verificar_exercicio", "Registro21", "Registro27",
    "BRASIL", "nome_pais", "pais_existe",
    "CAIXA", "banco_existe", "nome_banco",
    "CNPJ_OBRIGATORIO", "CONTA_BANCARIA", "REGISTRO_BEM_MOVEL", "REGISTRO_IMOVEL", "tem_cnpj_cpf", "SOMENTE_BRASIL", "SOMENTE_EXTERIOR", "TITULAR_OU_DEPENDENTE", "campos_aplicaveis",
    "campos_obrigatorios",
    "esta_na_tabela", "renavam_valido",
    "codigo_existe", "nome_codigo",
    "Registro25", "Registro26", "Registro35", "tabela_dependentes", "tabela_pagamentos", "erro_nome_pessoa",
]
