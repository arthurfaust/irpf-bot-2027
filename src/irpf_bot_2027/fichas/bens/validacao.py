"""
Validação de um bem do JSON antes de gravar no DBK.

Três checagens, nesta ordem:
    1. os campos e blocos do JSON são conhecidos, os obrigatórios estão presentes e os valores
       convertem (entrada.py)
    2. o grupo/código existe (tabela_bens.py)
    3. cada campo preenchido aparece na tela para esse grupo/código/país (regras.py)

Origem: não tem regras próprias; usa as dos três módulos acima (veja a origem em cada um).
"""

from irpf_bot_2027.fichas.bens.entrada import ORIGEM_NO_JSON, converter_campos
from irpf_bot_2027.leiautes.atual import BRASIL, campos_aplicaveis, codigo_existe, nome_codigo

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
