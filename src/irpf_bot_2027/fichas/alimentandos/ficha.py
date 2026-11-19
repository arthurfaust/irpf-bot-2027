"""
Ficha Alimentandos (registro 35).

Cada item do JSON é um alimentando:

    {"nome": "MARIA X", "cpf": "333.444.555-08", "data_nascimento": "2012-03-20", "residente": "brasil",
     "alimentando_de": "770.396.770-08",
     "decisao_judicial": {"data": "2024-02-10", "processo": "0001234-56.2024.8.26.0100", "vara": "1",
                          "comarca": "Sao Paulo", "uf": "SP"},
     "escritura_publica": {"data": "2023-03-15", "cnpj_cartorio": "00.000.000/0001-91",
                           "nome_cartorio": "Cartorio X", "livro": "12", "folhas": "34", "uf": "SP",
                           "cod_municipio": "7107", "municipio": "Sao Paulo"}}

    - obrigatórios: nome, cpf, data_nascimento, residente ("brasil" ou "exterior"), alimentando_de (CPF
      do titular ou de um dependente) e pelo menos um dos blocos decisao_judicial / escritura_publica,
      cada um com a data; os dois juntos são o tipo de processo "ambos".

Busca pelo CPF, só nas linhas do DBK de entrada (docs/adr/0025): igual à dos dependentes (ADR 0024).
"alimentando_de" precisa ser o titular ou um dependente do DBK (os dependentes do JSON já foram
gravados antes); senão, revisão. CPF de dependente do DBK também vai para revisão.

A confirmação "Os alimentandos atendem aos requisitos?" não é gravada no DBK: o programa volta a pedir
depois de cada restauração (roteiro de 18/11/2026). O relatório lembra de marcá-la.

Origem:
    - Regras da tela: classes Alimentando, DecisaoJudicial, EscrituracaoPublica e validadores do IRPF
      2026 (lidas com javap): nome com a regra do ValidadorNomeIRPF; residência, nascimento,
      "Alimentando do" e tipo de processo obrigatórios; CPF obrigatório para residente no Brasil (o bot
      exige sempre: é a chave da busca e da ligação com os pagamentos — escolha do projeto), diferente
      do titular, de outro alimentando, de dependente e do "Alimentando do"; data da decisão ou da
      lavratura obrigatória conforme o tipo, entre o nascimento e 31/12 do ano-calendário; CNPJ do
      cartório com dígito.
    - UFs: os arquivos lib/resources/<UF>.xml do programa. O código e o nome do município vêm do JSON,
      como nos imóveis (não conferidos com a tabela).
    - Confirmado em DBK gravado pelo programa em 18/11/2026 (tests/dados/alimentandos_programa.DBK, 3
      alimentandos: decisão judicial, escritura pública e ambos): residência 0 Brasil / 1 exterior;
      chave em sequência na ordem de digitação; tipo de processo J, C ou A; campos do bloco não usado em
      branco (código do município 0000); "Alimentando do" gravado com o CPF.
    - Importação da declaração anterior: traz chave, nome, CPF e "Alimentando do", sem data de
      nascimento e sem tipo de processo (tests/dados/pagamentos_importados.DBK).
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from irpf_bot_2027.comum.conversoes import data_do_dbk, so_digitos
from irpf_bot_2027.comum.documentos import cnpj_valido, cpf_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import ANO_CALENDARIO, Registro25, Registro35, erro_nome_pessoa

logger = logging.getLogger(__name__)

NOME = "Alimentandos"
CHAVE_JSON = "alimentandos"

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

# --- validação ---

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
    for chave in sorted(set(item) - set(CAMPOS_JSON)):
        erros.append(f"campo desconhecido '{chave}'")
    for chave in OBRIGATORIOS:
        if not _informado(item, chave):
            erros.append(f"campo obrigatório '{chave}' não informado")

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

# --- gravação ---

def montar_linha(campos: dict, cpf: str, chave: int) -> str:
    linha = Registro35.linha_vazia()
    linha = Registro35.TIPO_REGISTRO.gravar(linha, 35)
    linha = Registro35.CPF.gravar(linha, cpf)
    linha = Registro35.CHAVE.gravar(linha, chave)
    for nome, valor in campos.items():
        linha = getattr(Registro35, nome).gravar(linha, valor)
    return Registro35.gravar_cod_controle(linha)        # sempre por último

def _em_branco(campo, linha: str) -> bool:
    valor = campo.ler(linha).strip()
    return not valor or (campo.tipo == "N" and int(valor) == 0)

ROTULOS = {"NOME": "nome", "CPF_ALIMENTANDO": "cpf", "DATA_NASCIMENTO": "data_nascimento",
           "RESIDENCIA": "residente", "CPF_VINCULADO": "alimentando_de", "TIPO_PROCESSO": "tipo de processo",
           **{campo: f"{bloco}.{chave}" for bloco, mapa in BLOCOS.items() for chave, campo in mapa.items()}}

def atualizar_linha(linha: str, campos: dict) -> tuple[str, list[str]]:
    """Alimentando encontrado: campo em branco recebe o valor do JSON; preenchido e diferente fica e
    entra na lista devolvida (nomes dos campos do JSON, sem os valores). A residência 0 (Brasil) conta
    como resposta."""
    diferentes = []
    for nome, valor in campos.items():
        campo = getattr(Registro35, nome)
        if nome != "RESIDENCIA" and _em_branco(campo, linha):
            linha = campo.gravar(linha, valor)
        elif campo.ler(linha) != campo.formatar(valor):
            diferentes.append(ROTULOS[nome])
    return Registro35.gravar_cod_controle(linha), diferentes

@dataclass
class Resultado:
    """Alimentandos do JSON pelo número (a partir de 1); do DBK pela ordem na ficha (a partir de 1)."""
    encontrados: list[int] = field(default_factory=list)
    novos: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)
    diferentes: list[int] = field(default_factory=list)
    dbk_nao_informados: list[int] = field(default_factory=list)
    com_alimentandos: bool = False                              # lembrar a confirmação dos requisitos

def inserir(arquivo: ArquivoDBK, itens: list[dict], campos_por_item: list[dict]) -> Resultado:
    resultado = Resultado()
    cpf = arquivo.cpf_declarante
    entrada = arquivo.indices(Registro35.TIPO)             # os novos entram depois: posições não mudam
    dependentes = {Registro25.CPF_DEPENDENTE.ler(l).strip() for l in arquivo.linhas_do_tipo(Registro25.TIPO)}
    usados = set()

    for numero, campos in enumerate(campos_por_item, start=1):
        descricao = f"Alimentando {numero}"
        if campos["CPF_ALIMENTANDO"] in dependentes:
            logger.warning("%s: o CPF é de um dependente do DBK; não foi gravado (revisão).", descricao)
            resultado.revisao.append(numero)
            continue
        if campos["CPF_VINCULADO"] != cpf and campos["CPF_VINCULADO"] not in dependentes:
            logger.warning("%s: 'alimentando_de' não é o titular nem um dependente do DBK; não foi gravado "
                           "(revisão).", descricao)
            resultado.revisao.append(numero)
            continue
        encontrados = [(ordem, posicao) for ordem, posicao in enumerate(entrada, start=1)
                       if Registro35.CPF_ALIMENTANDO.ler(arquivo.linhas[posicao]).strip() == campos["CPF_ALIMENTANDO"]]
        if len(encontrados) > 1:
            logger.warning("%s: %d alimentandos no DBK com o mesmo CPF; não foi gravado (revisão).",
                           descricao, len(encontrados))
            resultado.revisao.append(numero)
            usados.update(ordem for ordem, _ in encontrados)
            continue
        if encontrados:
            ordem, posicao = encontrados[0]
            usados.add(ordem)
            nova, diferentes = atualizar_linha(arquivo.linhas[posicao], campos)
            arquivo.substituir(posicao, nova)
            if diferentes:
                logger.warning("%s: no DBK, campo(s) diferente(s) do JSON mantido(s): %s.", descricao,
                               ", ".join(diferentes))
                resultado.diferentes.append(numero)
            logger.info("%s encontrado no DBK (linha %d)", descricao, posicao + 1)
            resultado.encontrados.append(numero)
            continue

        chaves = [int(Registro35.CHAVE.ler(l)) for l in arquivo.linhas_do_tipo(Registro35.TIPO)]
        posicao = arquivo.inserir(Registro35.TIPO, montar_linha(campos, cpf, max(chaves, default=0) + 1))
        logger.info("%s inserido na linha %d", descricao, posicao + 1)
        resultado.novos.append(numero)

    resultado.dbk_nao_informados = [ordem for ordem in range(1, len(entrada) + 1) if ordem not in usados]
    resultado.com_alimentandos = bool(arquivo.indices(Registro35.TIPO))
    return resultado

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Alimentandos do DBK no formato do JSON de entrada, com a chave em "dbk" (docs/adr/0026).
    Campo em branco no DBK (ex.: nascimento e processo do importado) não sai no JSON."""
    residencias = {codigo: nome for nome, codigo in RESIDENCIA.items()}
    blocos_do_tipo = {tipo: blocos for blocos, tipo in TIPO_PROCESSO.items()}
    itens = []
    for linha in arquivo.linhas_do_tipo(Registro35.TIPO):
        ler = lambda nome: getattr(Registro35, nome).ler(linha).strip()
        item = {"nome": ler("NOME"), "cpf": ler("CPF_ALIMENTANDO"),
                "data_nascimento": data_do_dbk(ler("DATA_NASCIMENTO")),
                "residente": residencias.get(int(ler("RESIDENCIA") or 0)), "alimentando_de": ler("CPF_VINCULADO")}
        for nome_bloco in blocos_do_tipo.get(ler("TIPO_PROCESSO"), ()):
            bloco = {}
            for chave, nome_campo in BLOCOS[nome_bloco].items():
                valor = ler(nome_campo)
                if chave == "data":
                    valor = data_do_dbk(valor)
                elif nome_campo == "COD_MUNICIPIO" and not valor.strip("0"):
                    valor = None
                if valor:
                    bloco[chave] = valor
            item[nome_bloco] = bloco
        item = {chave: valor for chave, valor in item.items() if valor not in (None, "")}
        item["dbk"] = {"chave": int(ler("CHAVE"))}
        itens.append(item)
    return itens

def relatorio(resultado: Resultado) -> list[tuple[int, str]]:
    def numeros(lista: list[int]) -> str:
        return ", ".join(map(str, lista))

    linhas = [(logging.INFO, f"{NOME}: {len(resultado.encontrados)} encontrado(s), {len(resultado.novos)} novo(s), "
                             f"{len(resultado.revisao)} para revisão")]
    if resultado.encontrados:
        linhas.append((logging.INFO, "  encontrados no DBK, campos em branco preenchidos (alimentandos do JSON): "
                                     f"{numeros(resultado.encontrados)}"))
    if resultado.novos:
        linhas.append((logging.INFO, f"  lançados como novos (alimentandos do JSON): {numeros(resultado.novos)}"))
    if resultado.diferentes:
        linhas.append((logging.WARNING, "  CONFERIR, campos do DBK diferentes do JSON, mantidos (alimentandos do "
                                        f"JSON): {numeros(resultado.diferentes)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, f"  REVISÃO, não gravados (alimentandos do JSON): {numeros(resultado.revisao)}"))
    if resultado.dbk_nao_informados:
        linhas.append((logging.WARNING, "  REVISÃO, alimentandos do DBK que não vieram no JSON (itens da ficha): "
                                        f"{numeros(resultado.dbk_nao_informados)}"))
    if resultado.com_alimentandos:
        linhas.append((logging.WARNING, "  NO PROGRAMA, marque \"Estou ciente de que os alimentandos informados "
                                        "devem se enquadrar nos requisitos\" (não é gravado no DBK)"))
    return linhas
