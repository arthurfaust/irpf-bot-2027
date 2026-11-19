"""
Validação dos pagamentos do JSON (ficha Pagamentos Efetuados, registro 26).

Regras de cada código: leiautes/irpf2026/tabela_pagamentos.py (classes Pagamento e
PainelPagamentosDetalhe do IRPF 2026, lidas com javap). Valor pago maior que zero e nome obrigatório
(o programa só avisa em alguns códigos): escolha do projeto, para não gravar pagamento incompleto.
"""

from irpf_bot_2027.comum.conversoes import so_digitos, valor_em_reais
from irpf_bot_2027.comum.documentos import cnpj_valido, cpf_valido, ni_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.fichas import referencia
from irpf_bot_2027.leiautes.atual import BRASIL, Registro26, pais_existe
from irpf_bot_2027.leiautes.atual import tabela_pagamentos as tabela

CAMPOS_JSON = ("codigo", "tipo", "cpf_dependente_alimentando", "cnpj_cpf", "nome", "valor_pago",
               "parcela_nao_dedutivel", "descricao", "pais")
TIPOS_JSON = {"T": "titular", "D": "dependente", "A": "alimentando"}
CPF, CNPJ = 1, 2                                    # Registro26.TIPO_NI

def _informado(item: dict, chave: str) -> bool:
    return item.get(chave) is not None and str(item[chave]).strip() != ""

def _texto(item: dict, chave: str, tamanho: int, erros: list[str]) -> str | None:
    texto = normalizar_texto(str(item[chave]))
    fora = caracteres_fora_do_latin1(texto.upper())
    if fora:
        erros.append(f"'{chave}': caractere(s) não aceito(s) pelo programa: {', '.join(repr(c) for c in fora)}")
    elif len(texto) > tamanho:
        erros.append(f"'{chave}': tem {len(texto)} caracteres; o máximo é {tamanho}")
    else:
        return texto
    return None

def _valor(item: dict, chave: str, erros: list[str]):
    try:
        return valor_em_reais(item[chave])
    except ValueError as erro:
        erros.append(f"'{chave}': {erro}")
        return None

def _validar_ni(codigo: str, ni: str, erros: list[str]) -> int | None:
    """Tipo do CPF/CNPJ (1 ou 2) ou None, com o erro do formato que o código aceita."""
    if codigo in tabela.CPF_OBRIGATORIO:
        aceito, formato = cpf_valido(ni), "CPF (11 dígitos)"
    elif codigo in tabela.CNPJ_OBRIGATORIO:
        aceito, formato = cnpj_valido(ni), "CNPJ (14 dígitos)"
    else:
        aceito, formato = ni_valido(ni), "CPF (11 dígitos) ou CNPJ (14 dígitos)"
    if not aceito:
        erros.append(f"'cnpj_cpf': {formato} inválido")
        return None
    return CPF if len(ni) == 11 else CNPJ

def validar_item(item: dict, cpf_declarante: str | None) -> tuple[dict, list[str]]:
    """Campos do Registro26 já convertidos (mais as chaves internas _codigo e _cpf_vinculado) e os erros.
    As mensagens não repetem os dados."""
    campos, erros = {}, []
    if not isinstance(item, dict):
        return campos, ["esperado um objeto com os campos do pagamento"]
    for chave in sorted(set(item) - set(CAMPOS_JSON) - referencia.CAMPOS_DE_CONTROLE):
        erros.append(f"campo desconhecido '{chave}'")
    erros += referencia.validar(item, "item")

    codigo = str(item.get("codigo", "")).strip()
    if not codigo:
        return campos, erros + ["campo obrigatório 'codigo' não informado"]
    if not tabela.codigo_existe(codigo):
        return campos, erros + [f"'codigo': esperado um dos códigos da ficha ({', '.join(tabela.CODIGOS)})"]
    campos["CODIGO"] = int(codigo)
    pensao = codigo in tabela.PENSAO

    def nao_se_aplica(chave: str) -> None:
        if _informado(item, chave):
            erros.append(f"'{chave}' não se aplica ao código {codigo}")

    def obrigatorio(chave: str) -> bool:
        if not _informado(item, chave):
            erros.append(f"campo obrigatório '{chave}' não informado (código {codigo})")
            return False
        return True

    # tipo do pagamento e dependente/alimentando
    tipos = tabela.TIPOS.get(codigo, set())
    tipo = "A" if pensao else ""
    if tipos:
        if obrigatorio("tipo"):
            tipo = str(item["tipo"]).strip().upper()
            if tipo not in tipos:
                erros.append(f"'tipo': esperado {' ou '.join(repr(t) for t in sorted(tipos, key='TDA'.index))} "
                             f"({', '.join(TIPOS_JSON[t] for t in sorted(tipos, key='TDA'.index))})")
                tipo = ""
    else:
        nao_se_aplica("tipo")
    campos["TIPO_PAGAMENTO"] = tipo
    if tipo in ("D", "A"):
        if obrigatorio("cpf_dependente_alimentando"):
            cpf = so_digitos(item["cpf_dependente_alimentando"])
            if not cpf_valido(cpf):
                erros.append("'cpf_dependente_alimentando': CPF (11 dígitos) inválido")
            else:
                campos["_cpf_vinculado"] = cpf
    else:
        nao_se_aplica("cpf_dependente_alimentando")

    # beneficiário
    if pensao:
        nao_se_aplica("cnpj_cpf")
        nao_se_aplica("nome")
    else:
        if codigo in tabela.EXTERIOR:
            nao_se_aplica("cnpj_cpf")
        elif _informado(item, "cnpj_cpf") or codigo not in tabela.NI_OPCIONAL:
            if obrigatorio("cnpj_cpf"):
                ni = so_digitos(item["cnpj_cpf"])
                tipo_ni = _validar_ni(codigo, ni, erros)
                if tipo_ni and ni == cpf_declarante:
                    erros.append("'cnpj_cpf': o beneficiário não pode ser o próprio declarante")
                elif tipo_ni and ni == campos.get("_cpf_vinculado"):
                    erros.append(f"'cnpj_cpf': o beneficiário não pode ser o próprio {TIPOS_JSON[tipo]}")
                elif tipo_ni:
                    campos["NI_BENEFICIARIO"], campos["TIPO_NI"] = ni, tipo_ni
        if obrigatorio("nome"):
            nome = _texto(item, "nome", Registro26.NOME_BENEFICIARIO.tamanho, erros)
            if nome:
                campos["NOME_BENEFICIARIO"] = nome

    # valores
    if obrigatorio("valor_pago"):
        valor = _valor(item, "valor_pago", erros)
        if valor is not None and valor == 0:
            erros.append("'valor_pago': o valor pago não pode ser zero")
        elif valor is not None:
            campos["VALOR_PAGO"] = valor
    if codigo in tabela.COM_PARCELA_NAO_DEDUTIVEL:
        if _informado(item, "parcela_nao_dedutivel"):
            parcela = _valor(item, "parcela_nao_dedutivel", erros)
            if parcela is not None and "VALOR_PAGO" in campos and parcela > campos["VALOR_PAGO"]:
                erros.append("'parcela_nao_dedutivel': maior que o valor pago")
            elif parcela is not None:
                campos["PARCELA_NAO_DEDUTIVEL"] = parcela
    else:
        nao_se_aplica("parcela_nao_dedutivel")

    # descrição e país
    if codigo in tabela.DESCRICAO_OBRIGATORIA:
        obrigatorio("descricao")
    if _informado(item, "descricao"):
        descricao = _texto(item, "descricao", Registro26.DESCRICAO.tamanho, erros)
        if descricao:
            campos["DESCRICAO"] = descricao
    if codigo in tabela.EXTERIOR:
        if obrigatorio("pais"):
            pais = str(item["pais"]).strip()
            if not pais.isdigit() or len(pais) > 3 or not pais_existe(pais.zfill(3)) or pais.zfill(3) == BRASIL:
                erros.append("'pais': esperado o código de um país do exterior com até 3 dígitos (ex.: \"249\")")
            else:
                campos["PAIS"] = pais.zfill(3)
    else:
        nao_se_aplica("pais")
    return campos, erros

def validar(itens: list[dict], cpf_declarante: str | None = None) -> tuple[list[dict], list[str]]:
    campos_por_item, erros = [], []
    for numero, item in enumerate(itens, start=1):
        campos, erros_item = validar_item(item, cpf_declarante)
        campos_por_item.append(campos)
        erros.extend(f"pagamento {numero}: {erro}" for erro in erros_item)
    return campos_por_item, erros
