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
ORIGEM = "origem"           # de quais documentos o item saiu (docs/adr/0028); o bot só confere o formato
CAMPOS_DE_CONTROLE = {CAMPO, ORIGEM}


def validar_origem(item: dict) -> list[str]:
    """"origem": [{"documento": "nome do arquivo", "pagina": 2}, ...]; página opcional. Não vai para o DBK
    nem para o log (o nome do documento pode identificar o cliente)."""
    if ORIGEM not in item:
        return []
    origem = item[ORIGEM]
    formato = f"'{ORIGEM}': esperada uma lista de {{\"documento\": \"...\", \"pagina\": N}} (página opcional)"
    if not isinstance(origem, list) or not origem:
        return [formato]
    for fonte in origem:
        if not isinstance(fonte, dict) or not set(fonte) <= {"documento", "pagina"}:
            return [formato]
        if not isinstance(fonte.get("documento"), str) or not fonte["documento"].strip():
            return [formato]
        pagina = fonte.get("pagina", 1)
        if isinstance(pagina, bool) or not isinstance(pagina, int) or pagina < 1:
            return [formato]
    return []


def validar(item: dict, chave_ref: str) -> list[str]:
    """Erros de formato dos campos de controle: "dbk" e "origem" (vazio se não vieram)."""
    erros = validar_origem(item)
    if CAMPO not in item:
        return erros
    referencia = item[CAMPO]
    formato = f'esperado {{"{chave_ref}": N}}, com N inteiro a partir de 1'
    if not isinstance(referencia, dict) or set(referencia) != {chave_ref}:
        return erros + [f"'{CAMPO}': {formato}"]
    valor = referencia[chave_ref]
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        return erros + [f"'{CAMPO}': {formato}"]
    return erros


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
    """O item sem os campos de controle ("dbk", "origem")."""
    return {chave: valor for chave, valor in item.items() if chave not in CAMPOS_DE_CONTROLE}
