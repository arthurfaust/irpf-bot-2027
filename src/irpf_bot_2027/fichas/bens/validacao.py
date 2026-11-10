"""
Validação de um bem do JSON antes de gravar no DBK.

Três checagens, nesta ordem:
    1. os campos e blocos do JSON são conhecidos, os obrigatórios estão presentes e os valores
       convertem (entrada.py) e cabem no campo do Registro27, com os textos normalizados (verificar_formato, comum/texto.py)
    2. o grupo/código existe (tabela_bens.py), o país existe (paises.py) e o código pode estar
       nesse país (regras.SOMENTE_BRASIL / SOMENTE_EXTERIOR)
    3. cada campo preenchido aparece na tela para esse grupo/código/país (regras.py)

Origem: não tem regras próprias; usa as dos três módulos acima (veja a origem em cada um).
"""

from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.fichas.bens.entrada import ORIGEM_NO_JSON, converter_campos
from irpf_bot_2027.leiautes.atual import (
    BRASIL, SOMENTE_BRASIL, SOMENTE_EXTERIOR, Registro27, campos_aplicaveis, codigo_existe, esta_na_tabela,
    nome_codigo, nome_pais, pais_existe,
)

def verificar_formato(campos: dict) -> list[str]:
    """Confere se cada valor cabe no seu campo do Registro27. Normaliza os textos no próprio dicionário.

    As mensagens não repetem o conteúdo dos textos, que pode ter dados do cliente.
    """
    erros = []
    for nome, valor in list(campos.items()):
        campo = getattr(Registro27, nome)
        origem = ORIGEM_NO_JSON.get(nome, nome)

        if campo.tipo != "N" and isinstance(valor, str):
            valor = campos[nome] = normalizar_texto(valor)
            gravado = valor.upper()                 # o Campo grava texto em maiúsculas
            fora = caracteres_fora_do_latin1(gravado)
            if fora:
                lista = ", ".join(f"'{c}' (U+{ord(c):04X})" for c in fora)
                erros.append(f"'{origem}': caractere(s) não aceito(s) pelo programa: {lista}")
                continue
            if len(gravado) > campo.tamanho:
                erros.append(f"'{origem}': tem {len(gravado)} caracteres; o máximo é {campo.tamanho}")
                continue

        try:
            campo.formatar(valor)
        except (ValueError, ArithmeticError):
            formato = f"número de {campo.tamanho} posições" + (f" com {campo.decimais} decimais" if campo.decimais else "")
            erros.append(f"'{origem}': valor inválido ou grande demais para o campo ({formato})")
    return erros

def validar_bem(bem: dict) -> tuple[dict, list[str]]:
    """
    Valida os dados de um bem. Se houver erros, o bem não deve ser gravado.
    Args:
        bem (dict): Dicionário com os dados do bem.
    Returns:
        tuple[dict, list[str]]: Tupla contendo:
            - Dicionário com os campos validados.
            - Lista de erros encontrados.
    """
    grupo, codigo = bem.get("grupo"), bem.get("codigo")

    campos, erros = converter_campos(bem)
    erros += verificar_formato(campos)
    pais = campos.get("PAIS")                       # já convertido para 3 dígitos

    if grupo is None or codigo is None or pais is None:
        return campos, erros                        # o erro de campo obrigatório ou de formato já está na lista
    if not codigo_existe(grupo, codigo):
        return campos, erros + [f"grupo/código {grupo}/{codigo} não existe"]
    if not pais_existe(pais):
        return campos, erros + [f"país {pais} não existe na tabela do programa"]

    descricao = f"{grupo}/{codigo} ({nome_codigo(grupo, codigo)})"
    if pais != BRASIL and esta_na_tabela(SOMENTE_BRASIL, grupo, codigo):
        erros.append(f"{descricao} só pode estar localizado no Brasil (país {BRASIL}); veio {pais} ({nome_pais(pais)})")
    if pais == BRASIL and esta_na_tabela(SOMENTE_EXTERIOR, grupo, codigo):
        erros.append(f"{descricao} só pode estar localizado no exterior; veio {BRASIL} (Brasil)")

    permitidos = campos_aplicaveis(
        grupo, codigo, pais,
        autocustodiante=campos.get("AUTOCUSTODIANTE") == 1,
        bolsa=campos.get("BOLSA") == 1,
    )
    local = "no Brasil" if pais == BRASIL else "no exterior"
    for campo in sorted(set(campos) - permitidos):
        motivo = " quando é autocustodiante" if campo == "CNPJ_CPF" and campos.get("AUTOCUSTODIANTE") == 1 else ""
        erros.append(f"'{ORIGEM_NO_JSON.get(campo, campo)}' não se aplica a {descricao} {local}{motivo}")

    return campos, erros
