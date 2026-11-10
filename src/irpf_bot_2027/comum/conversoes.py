"""
Conversões reaproveitáveis do formato amigável do JSON para o formato gravado no .DBK.

Cada função recebe o valor do JSON e devolve o valor pronto para Campo.gravar, ou levanta
ValueError com uma mensagem que explica o formato esperado.

Origem:
    - Indicadores sim/não gravados como 1/0 e titular/dependente como "T"/"D": descrição dos
      campos IN_* e IN_TIPO_BENEFIC no irpf.jar!/mapeamentoTxt.xml do programa IRPF2026 (versão 1.5).
    - Datas em DDMMAAAA: confirmado em DBK gravado pelo programa (data de aquisição 23/10/2020
      gravada como "23102020") e descrito como DDMMAAAA em outros campos do leiaute
      (ex.: DT_NASCIM). Atenção: alguns campos do leiaute usam AAAAMMDD; confira o campo antes de usar.
    - CPF, CNPJ e CEP só com dígitos: confirmados em DBKs gravados pelo programa (tests/dados/).
"""

from datetime import date

def sim_nao(valor) -> int:
    """true/false -> 1/0. Recusa textos e números para não aceitar respostas ambíguas."""
    if not isinstance(valor, bool):
        raise ValueError(f"esperado true ou false, veio {valor!r}")
    return 1 if valor else 0

def so_digitos(valor) -> str:
    """Remove pontos, traços, barras e espaços (CPF, CNPJ, CEP)."""
    return "".join(ch for ch in str(valor) if ch.isdigit())

def titular_dependente(valor) -> str:
    """"T"/"D" (maiúsculo ou minúsculo) -> "T"/"D"."""
    valor = str(valor).upper()
    if valor not in ("T", "D"):
        raise ValueError(f'esperado "T" ou "D", veio {valor!r}')
    return valor

def data_ddmmaaaa(valor) -> str:
    """"2020-10-23" -> "23102020"."""
    try:
        data = date.fromisoformat(str(valor))
    except ValueError:
        raise ValueError(f'esperada data no formato "AAAA-MM-DD", veio {valor!r}') from None
    return data.strftime("%d%m%Y")
