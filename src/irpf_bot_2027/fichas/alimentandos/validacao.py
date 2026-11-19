"""
Validação dos alimentandos do JSON (ficha Alimentandos, registro 35).

Regras: classes Alimentando, DecisaoJudicial, EscrituracaoPublica e validadores do IRPF 2026 (lidas com
javap); veja a origem de cada uma na docstring de ficha.py.
"""

from collections import Counter
from datetime import date

from irpf_bot_2027.comum.conversoes import so_digitos
from irpf_bot_2027.comum.documentos import cnpj_valido, cpf_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.fichas import referencia
from irpf_bot_2027.leiautes.atual import ANO_CALENDARIO, Registro35, erro_nome_pessoa

CAMPOS_JSON = ("nome", "cpf", "data_nascimento", "residente", "alimentando_de", "decisao_judicial",
               "escritura_publica")
OBRIGATORIOS = ("nome", "cpf", "data_nascimento", "residente", "alimentando_de")
RESIDENCIA = {"brasil": 0, "exterior": 1}
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE",
       "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}

# bloco -> {chave do JSON: campo do Registro35}; a data de cada bloco é obrigatória.
BLOCOS = {
    "decisao_judicial": {"data": "DATA_DECISAO", "processo": "PROCESSO_JUDICIAL", "vara": "VARA_CIVIL",
                         "comarca": "COMARCA", "uf": "UF_COMARCA"},
    "escritura_publica": {"data": "DATA_LAVRATURA", "cnpj_cartorio": "CNPJ_CARTORIO",
                          "nome_cartorio": "NOME_CARTORIO", "livro": "LIVRO", "folhas": "FOLHA",
                          "uf": "UF_CARTORIO", "cod_municipio": "COD_MUNICIPIO", "municipio": "MUNICIPIO"},
}
TIPO_PROCESSO = {("decisao_judicial",): "J", ("escritura_publica",): "C",
                 ("decisao_judicial", "escritura_publica"): "A"}


def _informado(item: dict, chave: str) -> bool:
    return item.get(chave) is not None and str(item[chave]).strip() != ""

def _data(valor, rotulo: str, erros: list[str]) -> date | None:
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        erros.append(f"'{rotulo}': esperada data no formato \"AAAA-MM-DD\"")
        return None

def _texto(valor, rotulo: str, tamanho: int, erros: list[str]) -> str | None:
    texto = normalizar_texto(str(valor))
    fora = caracteres_fora_do_latin1(texto.upper())
    if fora:
        erros.append(f"'{rotulo}': caractere(s) não aceito(s) pelo programa: {', '.join(repr(c) for c in fora)}")
    elif len(texto) > tamanho:
        erros.append(f"'{rotulo}': tem {len(texto)} caracteres; o máximo é {tamanho}")
    else:
        return texto
    return None

def _validar_bloco(nome_bloco: str, bloco, nascimento: date | None, campos: dict, erros: list[str]) -> None:
    if not isinstance(bloco, dict):
        erros.append(f"'{nome_bloco}': esperado um objeto")
        return
    mapa = BLOCOS[nome_bloco]
    for chave in sorted(set(bloco) - set(mapa)):
        erros.append(f"campo desconhecido '{nome_bloco}.{chave}'")
    for chave, nome_campo in mapa.items():
        rotulo = f"{nome_bloco}.{chave}"
        if not _informado(bloco, chave):
            if chave == "data":
                erros.append(f"campo obrigatório '{rotulo}' não informado")
            continue
        valor = bloco[chave]
        campo = getattr(Registro35, nome_campo)
        if chave == "data":
            data = _data(valor, rotulo, erros)
            fim = date(int(ANO_CALENDARIO), 12, 31)
            if data and (data > fim or (nascimento and data < nascimento)):
                erros.append(f"'{rotulo}': deve estar entre a data de nascimento e 31/12/{ANO_CALENDARIO}")
            elif data:
                campos[nome_campo] = data.strftime("%d%m%Y")
        elif chave == "cnpj_cartorio":
            cnpj = so_digitos(valor)
            if not cnpj_valido(cnpj):
                erros.append(f"'{rotulo}': CNPJ (14 dígitos) inválido")
            else:
                campos[nome_campo] = cnpj
        elif chave == "uf":
            uf = str(valor).strip().upper()
            if uf not in UFS:
                erros.append(f"'{rotulo}': esperada a sigla de uma UF (ex.: \"SP\")")
            else:
                campos[nome_campo] = uf
        elif chave == "cod_municipio":
            codigo = str(valor).strip()
            if not codigo.isdigit() or len(codigo) > campo.tamanho:
                erros.append(f"'{rotulo}': esperado o código do município com até {campo.tamanho} dígitos")
            else:
                campos[nome_campo] = int(codigo)
        else:
            texto = _texto(valor, rotulo, campo.tamanho, erros)
            if texto:
                campos[nome_campo] = texto

def validar_item(item: dict, cpf_declarante: str | None) -> tuple[dict, list[str]]:
    """Campos do Registro35 já convertidos e os erros. As mensagens não repetem os dados."""
    campos, erros = {}, []
    if not isinstance(item, dict):
        return campos, ["esperado um objeto com os campos do alimentando"]
    for chave in sorted(set(item) - set(CAMPOS_JSON) - {referencia.CAMPO}):
        erros.append(f"campo desconhecido '{chave}'")
    for chave in OBRIGATORIOS:
        if not _informado(item, chave):
            erros.append(f"campo obrigatório '{chave}' não informado")
    erros += referencia.validar(item, "chave")

    if _informado(item, "nome"):
        nome = _texto(item["nome"], "nome", Registro35.NOME.tamanho, erros)
        if nome and erro_nome_pessoa(nome):
            erros.append(f"'nome': {erro_nome_pessoa(nome)}")
        elif nome:
            campos["NOME"] = nome

    if _informado(item, "cpf"):
        cpf = so_digitos(item["cpf"])
        if not cpf_valido(cpf):
            erros.append("'cpf': CPF (11 dígitos) inválido")
        elif cpf == cpf_declarante:
            erros.append("'cpf': o alimentando não pode ser o próprio declarante")
        else:
            campos["CPF_ALIMENTANDO"] = cpf

    nascimento = None
    if _informado(item, "data_nascimento"):
        nascimento = _data(item["data_nascimento"], "data_nascimento", erros)
        if nascimento and nascimento.year > int(ANO_CALENDARIO):
            erros.append(f"'data_nascimento': posterior ao ano-calendário {ANO_CALENDARIO}")
            nascimento = None
        elif nascimento:
            campos["DATA_NASCIMENTO"] = nascimento.strftime("%d%m%Y")

    if _informado(item, "residente"):
        residente = str(item["residente"]).strip().lower()
        if residente not in RESIDENCIA:
            erros.append("'residente': esperado \"brasil\" ou \"exterior\"")
        else:
            campos["RESIDENCIA"] = RESIDENCIA[residente]

    if _informado(item, "alimentando_de"):
        cpf_de = so_digitos(item["alimentando_de"])
        if not cpf_valido(cpf_de):
            erros.append("'alimentando_de': CPF (11 dígitos) inválido")
        elif cpf_de == campos.get("CPF_ALIMENTANDO"):
            erros.append("'alimentando_de': não pode ser o próprio alimentando")
        else:
            campos["CPF_VINCULADO"] = cpf_de

    blocos = tuple(b for b in BLOCOS if item.get(b) is not None)
    if not blocos:
        erros.append("informe 'decisao_judicial', 'escritura_publica' ou os dois (tipo de processo)")
    else:
        campos["TIPO_PROCESSO"] = TIPO_PROCESSO[blocos]
        for nome_bloco in blocos:
            _validar_bloco(nome_bloco, item[nome_bloco], nascimento, campos, erros)
    return campos, erros

def validar(itens: list[dict], cpf_declarante: str | None = None) -> tuple[list[dict], list[str]]:
    campos_por_item, erros = [], []
    for numero, item in enumerate(itens, start=1):
        campos, erros_item = validar_item(item, cpf_declarante)
        campos_por_item.append(campos)
        erros.extend(f"alimentando {numero}: {erro}" for erro in erros_item)
    repetidos = Counter(c["CPF_ALIMENTANDO"] for c in campos_por_item if "CPF_ALIMENTANDO" in c)
    for numero, campos in enumerate(campos_por_item, start=1):
        if repetidos[campos.get("CPF_ALIMENTANDO")] > 1:
            erros.append(f"alimentando {numero}: 'cpf': o mesmo CPF aparece em outro alimentando do JSON")
    return campos_por_item, erros
