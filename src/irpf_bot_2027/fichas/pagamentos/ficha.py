"""
Ficha Pagamentos Efetuados (registro 26).

Cada item do JSON é um pagamento:

    {"codigo": "10", "tipo": "T", "cnpj_cpf": "444.555.666-19", "nome": "MEDICO X",
     "valor_pago": "1500.00", "parcela_nao_dedutivel": "200.00", "descricao": "CONSULTAS"}

    - tipo: "T" titular, "D" dependente, "A" alimentando; só nos códigos que têm a pergunta
      (saúde e instrução: T/D/A; 36, 37 e 99: T/D). Com "D" ou "A", informe cpf_dependente_alimentando.
    - pensão alimentícia (30, 31, 33, 34): sem tipo, cnpj_cpf e nome; informe cpf_dependente_alimentando
      (o alimentando). O CPF e o nome do beneficiário vêm do alimentando no DBK, como faz o programa.
    - pais: obrigatório nos códigos do exterior (02, 15 a 20, 22, 31, 34); não se aplica aos demais.
    - descricao: obrigatória no 99; opcional nos demais.

Dependente e alimentando são procurados pelo CPF nos registros 25 e 35 do DBK (docs/adr/0021). Sem
eles no DBK, o pagamento não é gravado (revisão): a ficha de dependentes ainda não existe.

Busca (docs/adr/0021): o pagamento é identificado por código, tipo, dependente/alimentando e
CPF/CNPJ do beneficiário (no exterior, sem CPF/CNPJ, pelo nome), só nas linhas do DBK de entrada
(docs/adr/0023):
    1 pagamento sem valores no DBK  -> recebe os valores do JSON (pagamento trazido da declaração
                                       anterior) e a descrição, se estiver em branco;
    1 pagamento com valores no DBK  -> revisão (pode ser lançamento repetido);
    2 ou mais, ou 2 do JSON para 1  -> revisão;
    nenhum                          -> lançamento novo, na posição do código (docs/adr/0022), como o
                                       programa grava, para que os itens do relatório tenham a
                                       numeração da tela.

Origem:
    - Campos por código, obrigatoriedade e validações: leiautes/irpf2026/tabela_pagamentos.py
      (classes Pagamento e PainelPagamentosDetalhe do IRPF 2026, lidas com javap).
    - Campos gravados pelo programa (tipo do CPF/CNPJ, tipo do pagamento, chave, país 000 no Brasil,
      CPF e nome do alimentando na pensão): confirmados em DBK gravado em 18/11/2026
      (tests/dados/pagamentos_programa.DBK).
    - Importação da declaração anterior: traz todos os campos menos o valor pago e a parcela não
      dedutível, que ficam zerados, e o programa acusa "Valor Pago não foi informado" (erro).
      Confirmado em DBK importado do IRPF 2025 em 18/11/2026 (tests/dados/pagamentos_importados.DBK).
    - Valor pago maior que zero e nome obrigatório (o programa só avisa em alguns códigos): escolha do
      projeto, para não gravar pagamento incompleto.
"""

import logging
from collections import Counter
from dataclasses import dataclass, field

from irpf_bot_2027.comum.conversoes import numero_do_dbk, so_digitos, valor_em_reais
from irpf_bot_2027.comum.documentos import cnpj_valido, cpf_valido, ni_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import BRASIL, Registro25, Registro26, Registro35, pais_existe
from irpf_bot_2027.leiautes.atual import tabela_pagamentos as tabela

logger = logging.getLogger(__name__)

NOME = "Pagamentos Efetuados"
CHAVE_JSON = "pagamentos"

CAMPOS_JSON = ("codigo", "tipo", "cpf_dependente_alimentando", "cnpj_cpf", "nome", "valor_pago",
               "parcela_nao_dedutivel", "descricao", "pais")
TIPOS_JSON = {"T": "titular", "D": "dependente", "A": "alimentando"}
CPF, CNPJ = 1, 2                                    # Registro26.TIPO_NI

# --- validação ---

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
    for chave in sorted(set(item) - set(CAMPOS_JSON)):
        erros.append(f"campo desconhecido '{chave}'")

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

# --- dependentes e alimentandos do DBK ---

def vinculado_no_dbk(arquivo: ArquivoDBK, tipo: str, cpf: str) -> list[str]:
    """Linhas do dependente (registro 25) ou do alimentando (registro 35) com esse CPF."""
    registro, campo = (Registro25, Registro25.CPF_DEPENDENTE) if tipo == "D" else (Registro35, Registro35.CPF_ALIMENTANDO)
    return [linha for linha in arquivo.linhas_do_tipo(registro.TIPO) if campo.ler(linha).strip() == cpf]

def completar(campos: dict, tipo: str, linha_vinculado: str) -> dict:
    """Chave do dependente/alimentando e, na pensão, o CPF e o nome do alimentando (como o programa grava)."""
    campos = dict(campos)
    registro = Registro25 if tipo == "D" else Registro35
    campos["CHAVE_DEPENDENTE"] = int(registro.CHAVE.ler(linha_vinculado))
    if f"{campos['CODIGO']:02d}" in tabela.PENSAO:
        cpf = Registro35.CPF_ALIMENTANDO.ler(linha_vinculado).strip()
        campos["NOME_BENEFICIARIO"] = Registro35.NOME.ler(linha_vinculado).strip()
        if cpf:
            campos["NI_BENEFICIARIO"], campos["TIPO_NI"] = cpf, CPF
    return campos

# --- gravação ---

def montar_linha(campos: dict, cpf: str) -> str:
    linha = Registro26.linha_vazia()
    linha = Registro26.TIPO_REGISTRO.gravar(linha, 26)
    linha = Registro26.CPF.gravar(linha, cpf)
    for nome, valor in campos.items():
        if not nome.startswith("_"):
            linha = getattr(Registro26, nome).gravar(linha, valor)
    return Registro26.gravar_cod_controle(linha)        # sempre por último

def chave_busca(linha: str) -> tuple:
    """Código, tipo, chave do dependente/alimentando e beneficiário (CPF/CNPJ ou, sem ele, o nome)."""
    ni = Registro26.NI_BENEFICIARIO.ler(linha).strip()
    beneficiario = ni or normalizar_texto(Registro26.NOME_BENEFICIARIO.ler(linha)).upper()
    return (Registro26.CODIGO.ler(linha), Registro26.TIPO_PAGAMENTO.ler(linha).strip(),
            Registro26.CHAVE_DEPENDENTE.ler(linha), beneficiario)

VALORES = ("VALOR_PAGO", "PARCELA_NAO_DEDUTIVEL")

def sem_valores(linha: str) -> bool:
    """Pagamento trazido da declaração anterior: o programa importa tudo menos os valores."""
    return all(int(getattr(Registro26, nome).ler(linha)) == 0 for nome in VALORES)

def preencher_linha(linha: str, campos: dict) -> tuple[str, bool]:
    """Pagamento sem valores no DBK: grava os valores do JSON e a descrição, se estiver em branco.
    Devolve a linha e se a descrição do DBK, diferente da do JSON, foi mantida."""
    for nome in VALORES:
        linha = getattr(Registro26, nome).gravar(linha, campos.get(nome, 0))
    descricao_dbk = Registro26.DESCRICAO.ler(linha).strip()
    descricao_json = campos.get("DESCRICAO", "")
    if not descricao_dbk and descricao_json:
        linha = Registro26.DESCRICAO.gravar(linha, descricao_json)
    mantida = bool(descricao_dbk and descricao_json and descricao_dbk != descricao_json.upper())
    return Registro26.gravar_cod_controle(linha), mantida

@dataclass
class Resultado:
    """Pagamentos do JSON pelo número (a partir de 1); pagamentos do DBK pela ordem na ficha depois da
    gravação (a partir de 1), que é a numeração da tela, já que os novos entram na posição do código."""
    preenchidos: list[int] = field(default_factory=list)        # pagamento sem valores do DBK, preenchido
    novos: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)
    sem_vinculado: list[int] = field(default_factory=list)      # dependente/alimentando não está no DBK
    descricao_mantida: list[int] = field(default_factory=list)  # preenchidos com a descrição do DBK
    dbk_sem_valores: list[int] = field(default_factory=list)    # continuam sem valores: erro no programa
    dbk_nao_informados: list[int] = field(default_factory=list) # com valores, não vieram no JSON

def inserir(arquivo: ArquivoDBK, itens: list[dict], campos_por_item: list[dict]) -> Resultado:
    resultado = Resultado()
    cpf = arquivo.cpf_declarante
    entrada = arquivo.indices(Registro26.TIPO)              # posição atual de cada pagamento da entrada
    completos: dict[int, dict] = {}                         # pagamento do JSON -> campos com a chave
    linhas_completas: dict[int, str] = {}                   # pagamento do JSON -> linha montada

    for numero, campos in enumerate(campos_por_item, start=1):
        tipo = campos["TIPO_PAGAMENTO"]
        if tipo in ("D", "A"):
            vinculados = vinculado_no_dbk(arquivo, tipo, campos["_cpf_vinculado"])
            if len(vinculados) != 1:
                logger.warning("Pagamento %d: %s %s no DBK; não foi gravado (revisão).", numero, TIPOS_JSON[tipo],
                               "não encontrado" if not vinculados else "repetido")
                resultado.sem_vinculado.append(numero)
                continue
            campos = completar(campos, tipo, vinculados[0])
        completos[numero] = campos
        linhas_completas[numero] = montar_linha(campos, cpf)

    repetidos = Counter(chave_busca(linha) for linha in linhas_completas.values())
    usados = set()                                          # ordem (1...) dos pagamentos do DBK encontrados

    for numero, linha in linhas_completas.items():
        descricao = f"Pagamento {numero}"
        chave = chave_busca(linha)
        encontrados = [(ordem, posicao) for ordem, posicao in enumerate(entrada, start=1)
                       if chave_busca(arquivo.linhas[posicao]) == chave]
        usados.update(ordem for ordem, _ in encontrados)

        if len(encontrados) > 1:
            logger.warning("%s: %d pagamentos no DBK com o mesmo código, tipo e beneficiário; não foi gravado "
                           "(revisão).", descricao, len(encontrados))
            resultado.revisao.append(numero)
            continue
        if encontrados:
            ordem, posicao = encontrados[0]
            if not sem_valores(arquivo.linhas[posicao]):
                logger.warning("%s: já existe no DBK um pagamento com o mesmo código, tipo e beneficiário, com "
                               "valores; não foi gravado (revisão).", descricao)
                resultado.revisao.append(numero)
                continue
            if repetidos[chave] > 1:
                logger.warning("%s: outro pagamento do JSON tem o mesmo código, tipo e beneficiário e o DBK tem "
                               "só um; não foi gravado (revisão).", descricao)
                resultado.revisao.append(numero)
                continue
            nova, mantida = preencher_linha(arquivo.linhas[posicao], completos[numero])
            arquivo.substituir(posicao, nova)
            logger.info("%s: valores gravados no pagamento sem valores do DBK (linha %d)", descricao, posicao + 1)
            resultado.preenchidos.append(numero)
            if mantida:
                resultado.descricao_mantida.append(numero)
            continue

        posicao = arquivo.inserir(Registro26.TIPO, linha, ordenar_por=Registro26.CODIGO.ler)
        entrada = [p + 1 if p >= posicao else p for p in entrada]
        logger.info("%s inserido na linha %d", descricao, posicao + 1)
        resultado.novos.append(numero)

    final = arquivo.indices(Registro26.TIPO)                # o relatório usa a numeração da ficha já gravada
    for ordem, posicao in enumerate(entrada, start=1):
        item = final.index(posicao) + 1
        if sem_valores(arquivo.linhas[posicao]):
            resultado.dbk_sem_valores.append(item)
        elif ordem not in usados:
            resultado.dbk_nao_informados.append(item)
    return resultado

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Pagamentos do DBK no formato do JSON de entrada, com a ordem na ficha em "dbk" (docs/adr/0026).
    O dependente/alimentando sai pelo CPF (a chave do DBK é trocada pelo CPF do registro 25 ou 35)."""
    cpfs = {
        "D": {int(Registro25.CHAVE.ler(l)): Registro25.CPF_DEPENDENTE.ler(l).strip()
              for l in arquivo.linhas_do_tipo(Registro25.TIPO)},
        "A": {int(Registro35.CHAVE.ler(l)): Registro35.CPF_ALIMENTANDO.ler(l).strip()
              for l in arquivo.linhas_do_tipo(Registro35.TIPO)},
    }
    itens = []
    for ordem, linha in enumerate(arquivo.linhas_do_tipo(Registro26.TIPO), start=1):
        ler = lambda nome: getattr(Registro26, nome).ler(linha).strip()
        codigo, tipo = ler("CODIGO"), ler("TIPO_PAGAMENTO")
        pensao = codigo in tabela.PENSAO
        item = {"codigo": codigo, "tipo": tipo if codigo in tabela.TIPOS else None,
                "cpf_dependente_alimentando": cpfs.get(tipo, {}).get(int(ler("CHAVE_DEPENDENTE"))),
                "cnpj_cpf": None if pensao or codigo in tabela.EXTERIOR else ler("NI_BENEFICIARIO"),
                "nome": None if pensao else ler("NOME_BENEFICIARIO"),
                "valor_pago": numero_do_dbk(ler("VALOR_PAGO")),
                "parcela_nao_dedutivel": numero_do_dbk(ler("PARCELA_NAO_DEDUTIVEL"))
                if int(ler("PARCELA_NAO_DEDUTIVEL")) and codigo in tabela.COM_PARCELA_NAO_DEDUTIVEL else None,
                "descricao": ler("DESCRICAO"),
                "pais": ler("PAIS") if codigo in tabela.EXTERIOR else None}
        item = {chave: valor for chave, valor in item.items() if valor not in (None, "")}
        item["dbk"] = {"item": ordem}
        itens.append(item)
    return itens

def relatorio(resultado: Resultado) -> list[tuple[int, str]]:
    def numeros(lista: list[int]) -> str:
        return ", ".join(map(str, lista))

    linhas = [(logging.INFO, f"{NOME}: {len(resultado.preenchidos)} preenchido(s), {len(resultado.novos)} novo(s), "
                             f"{len(resultado.revisao) + len(resultado.sem_vinculado)} para revisão")]
    if resultado.preenchidos:
        linhas.append((logging.INFO, "  preenchidos (pagamentos sem valores do DBK; pagamentos do JSON): "
                                     f"{numeros(resultado.preenchidos)}"))
    if resultado.novos:
        linhas.append((logging.INFO, f"  lançados como novos (pagamentos do JSON): {numeros(resultado.novos)}"))
    if resultado.descricao_mantida:
        linhas.append((logging.WARNING, "  CONFERIR, preenchidos com a descrição do DBK, diferente da do JSON "
                                        f"(pagamentos do JSON): {numeros(resultado.descricao_mantida)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, "  REVISÃO, já existiam no DBK, não gravados (pagamentos do JSON): "
                                        f"{numeros(resultado.revisao)}"))
    if resultado.sem_vinculado:
        linhas.append((logging.WARNING, "  REVISÃO, dependente/alimentando não encontrado no DBK, não gravados "
                                        f"(pagamentos do JSON): {numeros(resultado.sem_vinculado)}"))
    if resultado.dbk_sem_valores:
        linhas.append((logging.WARNING, "  REVISÃO, pagamentos do DBK que continuam sem valores (o programa acusa "
                                        f"erro \"Valor Pago\"; itens da ficha): {numeros(resultado.dbk_sem_valores)}"))
    if resultado.dbk_nao_informados:
        linhas.append((logging.WARNING, "  REVISÃO, pagamentos do DBK com valores que não vieram no JSON (itens da "
                                        f"ficha): {numeros(resultado.dbk_nao_informados)}"))
    return linhas
