"""
Dígito verificador da conta bancária, como o programa calcula.

Origem: classe serpro.ppgd.irpf.negocio.resumo.ValidadorDvContaCorrente do IRPF 2026 (lida com javap),
usada nos bens com conta (Bem$20) e na conta de restituição. No programa, DV que não confere gera
**aviso** ("DV da conta inválido" / "Dígito verificador da conta corrente inválido"), sem impedir a
entrega; confirmado no roteiro geral em 19/11/2026.

    - Só confere quando conta e DV estão preenchidos e o DV tem 1 caractere (preValidar); banco fora da
      lista abaixo não é conferido. Qualquer caractere não numérico onde o cálculo espera número torna
      o DV inválido (o programa trata a exceção como DV inválido).
    - "Agência/conta formatada": completada com zeros à esquerda e cortada aos últimos N dígitos, com
      N da tabela irpf.jar!/bancos_calculo_dv.xml (TAMANHOS abaixo).
    - Tabelas de agências do Banco do Nordeste e do Banese: campos estáticos
      mapeamentoAgenciasBancoNordeste e mapeamentoAgenciasBanese da classe.
    - O Sicredi (748) é sempre aceito (validarDvBansicredi devolve true); o HSBC (399) não é conferido
      (não está na seleção de bancos do validador).
"""

# banco -> (dígitos da agência, dígitos da conta), de bancos_calculo_dv.xml (vigência 27/08/2019)
TAMANHOS = {
    "001": (4, 11), "003": (3, 6), "004": (3, 6), "021": (4, 9), "033": (4, 11), "037": (4, 9),
    "041": (4, 9), "047": (3, 8), "070": (4, 9), "104": (4, 8), "237": (4, 7), "341": (4, 5),
    "389": (4, 8), "422": (3, 6), "748": (4, 11), "756": (4, 9),
}

AGENCIAS_NORDESTE = dict(zip(*[iter("""
001 099 002 044 003 074 004 073 005 081 006 001 007 002 008 053 009 046 010 020 011 082 012 047 013 009
014 010 015 054 016 000 017 055 018 083 019 011 020 048 021 025 022 012 023 049 024 026 025 040 026 075
027 016 028 050 029 027 030 029 031 003 032 004 033 076 034 041 035 077 036 030 037 067 038 068 039 078
040 058 041 059 042 042 043 031 044 060 045 062 046 017 047 079 048 032 049 070 050 063 051 086 052 033
053 052 054 064 055 034 056 071 057 072 058 014 059 038 060 043 061 080 062 021 063 057 064 091 066 006
067 051 068 066 069 085 070 039 071 092 072 028 073 019 074 087 076 061 077 088 078 089 080 005 081 090
082 015 083 007 084 013 085 093 086 069 087 094 088 101 089 107 090 095 091 045 092 008 093 035 095 106
096 103 097 117 098 118 099 104 100 108 101 102 102 112 103 113 104 115 105 105 106 096 107 097 108 024
109 111 110 119 111 084 112 036 113 037 114 114 115 100 116 116 117 056 118 065 119 109
""".split())] * 2))

AGENCIAS_BANESE = dict(zip(*[iter("""
002 006 003 005 004 011 005 007 006 008 007 013 008 004 009 003 010 010 011 002 012 012 013 009 014 001
""".split())] * 2))


def _digitos(texto: str) -> list[int]:
    if not texto.isdigit():
        raise ValueError
    return [int(c) for c in texto]

def _zeros(texto: str, tamanho: int) -> str:
    """IRPFUtil.formatarZerosEsquerda: completa com zeros e fica com os últimos `tamanho` caracteres."""
    return texto.strip().rjust(tamanho, "0")[-tamanho:]

def modulo11(texto: str) -> int:
    """Pesos 2 a 9 a partir da direita; 11 - soma % 11 (pode dar 10 ou 11)."""
    soma = sum(d * (2 + i % 8) for i, d in enumerate(reversed(_digitos(texto))))
    return 11 - soma % 11

def modulo10(texto: str) -> int:
    """Pesos 2 e 1 a partir da direita, somando os algarismos de cada produto; 10 - soma % 10."""
    soma = 0
    for i, d in enumerate(reversed(_digitos(texto))):
        produto = d * (2 - i % 2)
        soma += produto // 10 + produto % 10
    return 10 - soma % 10

def _ponderado(texto: str, pesos: list[int]) -> int:
    digitos = _digitos(texto)
    return sum(digitos[i] * peso for i, peso in enumerate(pesos))

def _ate_9(valor: int) -> int:
    return 0 if valor >= 10 else valor

def calcular(banco: str, agencia: str, conta: str, dv: str) -> bool:
    """True se o DV confere (ou o banco é aceito sem cálculo). Levanta ValueError em caractere inválido."""
    tam_agencia, tam_conta = TAMANHOS.get(banco, (0, 0))
    ag = _zeros(agencia, tam_agencia) if tam_agencia else agencia.strip()
    cc = _zeros(conta, tam_conta) if tam_conta else conta.strip()
    bruta = conta.strip()

    if banco == "001":                                          # Banco do Brasil
        resto = modulo11(bruta)
        esperado = "x" if resto == 10 else "0" if resto > 10 else str(resto)
        return esperado == dv.lower().strip()
    if banco in ("037", "070"):                                 # Banpará, BRB
        return _ate_9(modulo11(bruta)) == int(dv)
    if banco in ("003", "047", "422"):
        if banco == "047":                                      # Banese
            ag = AGENCIAS_BANESE.get(ag, ag)
        resultado = modulo11(ag + cc)
        if banco == "422":                                      # Safra: 10 -> 0, 11 -> 1
            resultado = {10: 0, 11: 1}.get(resultado, resultado)
        else:                                                   # Amazônia, Banese: 10 ou 11 -> 0
            resultado = _ate_9(resultado)
        return resultado == int(dv)
    if banco == "004":                                          # Banco do Nordeste
        ag = AGENCIAS_NORDESTE.get(ag, ag)
        soma = sum(d * (2 + i % 8) for i, d in enumerate(reversed(_digitos(cc))))
        soma += sum(d * (7 + i % 8) for i, d in enumerate(reversed(_digitos(ag))))
        resto = soma % 11
        return (0 if resto in (0, 1) else 11 - resto) == int(dv)
    if banco == "021":                                          # Banestes
        return _ate_9(modulo10(bruta)) == int(dv)
    if banco in ("341", "389"):                                 # Itaú, Mercantil
        return _ate_9(modulo10(ag + cc)) == int(dv)
    if banco == "033":                                          # Santander
        pesos = [9, 7, 3, 1, 0, 0, 0, 9, 7, 1, 3, 1, 9, 7, 3]
        texto = ag + cc
        if len(texto) < len(pesos):
            raise ValueError
        soma = sum((d * p) % 10 for d, p in zip(_digitos(texto[:len(pesos)]), pesos))
        return _ate_9(10 - soma % 10) == int(dv)
    if banco == "041":                                          # Banrisul
        resto = 11 - _ponderado(cc, [3, 2, 4, 7, 6, 5, 4, 3, 2]) % 11
        resultado = 6 if resto == 10 else 0 if resto == 11 else resto
        return resultado == int(dv)
    if banco == "104":                                          # Caixa (só a conta, 9 dígitos)
        resultado = _ate_9(_ponderado(_zeros(bruta, 9), [2, 9, 8, 7, 6, 5, 4, 3, 2]) * 10 % 11)
        return resultado == int(dv)
    if banco == "237":                                          # Bradesco (aceita P quando o resto é 1)
        resto = sum(d * (2 + i % 6) for i, d in enumerate(reversed(_digitos(bruta)))) % 11
        esperado = "0" if resto in (0, 1) else str(11 - resto)
        informado = "0" if dv.lower() == "p" and resto == 1 else dv.lower()
        return esperado == informado
    if banco == "745":                                          # Citibank
        soma = sum(d * (2 + i % 8) for i, d in enumerate(reversed(_digitos(bruta))))
        return _ate_9(soma * 10 % 11) == int(dv)
    if banco == "748":                                          # Sicredi: sempre aceito
        return True
    if banco == "756":                                          # Sicoob
        soma = sum(d * (2 + i % 9) for i, d in enumerate(reversed(_digitos(bruta))))
        return _ate_9(11 - soma % 11) == int(dv)
    return True

def dv_confere(banco: str, agencia, conta, dv) -> bool:
    """O DV da conta confere com o cálculo do programa? True quando não há o que conferir."""
    conta, dv = str(conta or "").strip(), str(dv or "").strip()
    if not conta or not dv:
        return True                                     # o programa só confere com os dois preenchidos
    if len(dv) != 1:
        return False                                    # preValidar: DV de um caractere
    try:
        return calcular(str(banco or "").zfill(3), str(agencia or ""), conta, dv)
    except ValueError:
        return False
