"""
Dígitos verificadores de CPF e CNPJ.

Origem: algoritmo módulo 11 da Receita Federal, o mesmo que o programa IRPF aplica no campo NI
(serpro.ppgd.negocio.validadoresBasicos.ValidadorNI, nível ERRO na ficha de rendimentos de PJ).
Números com todos os dígitos iguais (ex.: 111.111.111-11) são recusados, como faz a Receita.
"""

def _digito(numeros: str, pesos: list[int]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos)) % 11
    return "0" if resto < 2 else str(11 - resto)

def cpf_valido(cpf: str) -> bool:
    """CPF só com dígitos (11) e os dois verificadores corretos."""
    if len(cpf) != 11 or not cpf.isdigit() or len(set(cpf)) == 1:
        return False
    d1 = _digito(cpf[:9], list(range(10, 1, -1)))
    d2 = _digito(cpf[:9] + d1, list(range(11, 1, -1)))
    return cpf[9:] == d1 + d2

def cnpj_valido(cnpj: str) -> bool:
    """CNPJ só com dígitos (14) e os dois verificadores corretos."""
    if len(cnpj) != 14 or not cnpj.isdigit() or len(set(cnpj)) == 1:
        return False
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _digito(cnpj[:12], pesos)
    d2 = _digito(cnpj[:12] + d1, [6] + pesos)
    return cnpj[12:] == d1 + d2

def ni_valido(ni: str) -> bool:
    """CPF (11 dígitos) ou CNPJ (14 dígitos) válido."""
    return cpf_valido(ni) if len(ni) == 11 else cnpj_valido(ni)
