"""
Referência explícita ao item do DBK: o campo "dbk" do item do JSON (docs/adr/0027).

    bens, dependentes, alimentandos:   "dbk": {"chave": N}   (a chave do item no DBK)
    rendimentos de PJ, pagamentos:     "dbk": {"item": N}    (a ordem do item na ficha do DBK de entrada)

É o mesmo formato que a exportação gera (docs/adr/0026). Quem preenche é a etapa de IA, que compara os
documentos com o DBK exportado. A referência substitui a busca: o item indicado é tratado como se a
busca o tivesse encontrado, depois de conferido por cada ficha (existe, é do mesmo tipo e, havendo
identificador forte nos dois lados, é o mesmo). Sem "dbk", vale a busca de cada ficha.
"""

from collections import Counter

CAMPO = "dbk"


def validar(item: dict, chave_ref: str) -> list[str]:
    """Erros de formato do campo "dbk" (vazio se não veio)."""
    if CAMPO not in item:
        return []
    referencia = item[CAMPO]
    formato = f'esperado {{"{chave_ref}": N}}, com N inteiro a partir de 1'
    if not isinstance(referencia, dict) or set(referencia) != {chave_ref}:
        return [f"'{CAMPO}': {formato}"]
    valor = referencia[chave_ref]
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        return [f"'{CAMPO}': {formato}"]
    return []


def numero(item: dict, chave_ref: str) -> int | None:
    """N da referência, ou None se o item não traz "dbk" (o formato já foi conferido em validar)."""
    referencia = item.get(CAMPO) if isinstance(item, dict) else None
    return referencia[chave_ref] if referencia else None


def repetidas(itens: list[dict], chave_ref: str) -> set[int]:
    """Itens do JSON (a partir de 1) que apontam para o mesmo item do DBK que outro item do JSON."""
    numeros = [numero(item, chave_ref) for item in itens]
    contagem = Counter(n for n in numeros if n is not None)
    return {i for i, n in enumerate(numeros, start=1) if n is not None and contagem[n] > 1}


def sem_campo(item: dict) -> dict:
    """O item sem o campo "dbk" (para as validações que recusam campo desconhecido)."""
    return {chave: valor for chave, valor in item.items() if chave != CAMPO}
