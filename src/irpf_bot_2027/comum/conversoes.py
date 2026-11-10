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
    - Valores com casas decimais implícitas (ex.: R$ 1.000,00 gravado como 0000000100000): atributo
      Decimais do irpf.jar!/mapeamentoTxt.xml. O formato aceito no JSON ("1234.56") é escolha deste projeto.
"""

import re
from datetime import date
from decimal import Decimal
from functools import partial

NUMERO_DECIMAL = re.compile(r"-?\d+(\.\d+)?")

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

def numero(valor, casas: int, permite_negativo: bool = False) -> Decimal:
    """Número do JSON ("1234.56" ou 1234.56) -> Decimal, sem arredondar.

    Recusa vírgula decimal, separador de milhar, símbolo de moeda, mais casas decimais que o campo
    e negativos (quando não permitidos). As mensagens não repetem o valor, que é dado do cliente.
    """
    formato = f'"1234.{"567"[:casas]}"' if casas else '"1234"'     # "1234.56" (2 casas), "1234.5" (1 casa)
    if isinstance(valor, bool) or not isinstance(valor, (str, int, float)):
        raise ValueError(f"esperado um número no formato {formato}")

    texto = str(valor).strip()
    if not NUMERO_DECIMAL.fullmatch(texto):
        if "," in texto:
            raise ValueError(f"use ponto como separador decimal, sem separador de milhar: {formato}")
        raise ValueError(f"esperado um número no formato {formato}, sem símbolo de moeda ou espaços")

    convertido = Decimal(texto)
    if -convertido.as_tuple().exponent > casas:
        raise ValueError(f"no máximo {casas} casa(s) decimal(is): {formato}")
    if convertido < 0 and not permite_negativo:
        raise ValueError("o valor não pode ser negativo")
    return convertido

valor_em_reais = partial(numero, casas=2)