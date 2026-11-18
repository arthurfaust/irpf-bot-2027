"""
Tipos de dependente e regras da ficha Dependentes (registro 25) do IRPF 2026.

Origem:
    - TIPOS: lib/resources/dependencias.xml do programa IRPF2026 (vigência 05/03/2026), coluna COL3.
    - RACA_COR: irpf.jar!/racaCor.xml (vigência 10/12/2025); 0 = sem resposta.
    - Idade (Dependente$6 e $7, erro "Data de nascimento deve ser compatível com a relação de
      dependência"): nos tipos 21, 24 e 41 o dependente não pode ter nascido antes de 01/01 do
      ano-calendário menos 22; nos tipos 22 e 25, antes de 01/01 do ano-calendário menos 25.
      Pais e avós (31) mais novos que o titular só geram aviso (Dependente$8): não conferido aqui,
      porque o bot não lê a data de nascimento do titular.
"""

from irpf_bot_2027.leiautes.irpf2026 import ANO_CALENDARIO

TIPOS: dict[str, str] = {
    "11": "Companheiro(a) ou cônjuge",
    "21": "Filho(a) ou enteado(a) até 21 anos",
    "22": "Filho(a) ou enteado(a) cursando nível superior, até 24 anos",
    "23": "Filho(a) ou enteado(a) em qualquer idade, com deficiência",
    "24": "Irmãos, netos ou bisnetos até 21 anos com guarda judicial",
    "25": "Irmãos, netos ou bisnetos até 24 anos, com guarda judicial",
    "26": "Irmãos, netos ou bisnetos com deficiência e guarda judicial",
    "31": "Pais, avós e bisavós com ou sem rendimentos até R$ 28.467,20",
    "41": "Menor pobre, até 21 anos, com guarda judicial",
    "51": "Tutor ou curador de pessoa absolutamente incapaz",
}

RACA_COR: dict[str, int] = {"amarela": 1, "branca": 2, "indigena": 3, "parda": 4, "preta": 5}

# Tipo -> ano mínimo de nascimento (nascido em 01/01 desse ano ou depois).
NASCIDO_A_PARTIR_DE: dict[str, int] = {
    **{t: int(ANO_CALENDARIO) - 22 for t in ("21", "24", "41")},
    **{t: int(ANO_CALENDARIO) - 25 for t in ("22", "25")},
}

def tipo_existe(tipo: str) -> bool:
    return tipo in TIPOS
