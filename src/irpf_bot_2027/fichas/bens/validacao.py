"""
Validação de um bem do JSON antes de gravar no DBK.

Três checagens, nesta ordem:
    1. os campos e blocos do JSON são conhecidos, os obrigatórios estão presentes e os valores
       convertem (entrada.py) e cabem no campo do Registro27, com os textos normalizados (verificar_formato, comum/texto.py)
    2. o grupo/código existe (tabela_bens.py)
    3. cada campo preenchido aparece na tela para esse grupo/código/país (regras.py)

Origem: não tem regras próprias; usa as dos três módulos acima (veja a origem em cada um).
"""

from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.fichas.bens.entrada import ORIGEM_NO_JSON, converter_campos
from irpf_bot_2027.leiautes.atual import BRASIL, Registro27, campos_aplicaveis, codigo_existe, nome_codigo

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
    grupo, codigo, pais = bem.get("grupo"), bem.get("codigo"), str(bem.get("pais", ""))

    campos, erros = converter_campos(bem)
    erros += verificar_formato(campos)

    if grupo is None or codigo is None:
        return campos, erros                        # o erro de campo obrigatório já está na lista
    if not codigo_existe(grupo, codigo):
        return campos, erros + [f"grupo/código {grupo}/{codigo} não existe"]

    permitidos = campos_aplicaveis(
        grupo, codigo, pais,
        autocustodiante=campos.get("AUTOCUSTODIANTE") == 1,
        bolsa=campos.get("BOLSA") == 1,
    )
    local = "no Brasil" if pais == BRASIL else "no exterior"
    for campo in sorted(set(campos) - permitidos):
        motivo = " quando é autocustodiante" if campo == "CNPJ_CPF" and campos.get("AUTOCUSTODIANTE") == 1 else ""
        erros.append(
            f"'{ORIGEM_NO_JSON.get(campo, campo)}' não se aplica a "
            f"{grupo}/{codigo} ({nome_codigo(grupo, codigo)}) {local}{motivo}"
        )

    return campos, erros
