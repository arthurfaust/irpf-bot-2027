"""
Ficha Rendimentos Tributáveis Recebidos de PJ pelo Titular (registro 21).

Cada item do JSON é uma fonte pagadora (um informe de rendimentos):

    {"cnpj_cpf": "33.000.167/0001-01", "nome": "EMPRESA X LTDA", "rendimentos": "85000.00",
     "contribuicao_previdenciaria": "9000.00", "imposto_retido": "12000.00",
     "decimo_terceiro": "7000.00", "irrf_decimo_terceiro": "600.00"}

Busca pelo CPF/CNPJ da fonte, só nas linhas do DBK de entrada (docs/adr/0020):
    1 fonte sem valores no DBK  -> recebe os valores do JSON (fonte trazida da declaração anterior);
    1 fonte com valores no DBK  -> revisão (pode ser lançamento repetido);
    2 ou mais                    -> revisão;
    nenhuma                      -> lançamento novo.

Origem:
    - Regras da tela (classe RendPJTitular do IRPF 2026, lida com javap): CPF/CNPJ com dígito
      verificador (ValidadorNI, erro), diferente do CPF do declarante (erro), nome obrigatório (erro),
      valores só positivos (ValorPositivo), pendência "Faltam valores" (erro) se rendimentos,
      contribuição, 13º e imposto estiverem todos em branco; ColecaoRendPJTitular.getRendimentoVazioPorNIFontePagadora
      (fonte sem valores identificada pelo CPF/CNPJ).
    - Todos os campos obrigatórios no JSON (use "0.00"): escolha do projeto, para a IA não omitir valores.
      Fonte com os quatro valores principais zerados é recusada, como a pendência do programa.
    - A importação da declaração anterior traz as fontes com nome e CNPJ e os valores zerados
      (informado pelo Arthur em 17/11/2026): é o caso que a busca preenche.
"""

import logging
from collections import Counter
from dataclasses import dataclass, field

from irpf_bot_2027.comum.conversoes import numero_do_dbk, so_digitos, valor_em_reais
from irpf_bot_2027.comum.documentos import ni_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import referencia
from irpf_bot_2027.leiautes.atual import Registro21

logger = logging.getLogger(__name__)

NOME = "Rendimentos Tributáveis Recebidos de PJ pelo Titular"
CHAVE_JSON = "rendimentos_pj"
REF = "item"                        # "dbk": {"item": N}, a ordem da fonte na ficha do DBK (docs/adr/0027)

# JSON -> campo do Registro21
VALORES = {
    "rendimentos": "RENDIMENTOS",
    "contribuicao_previdenciaria": "CONTRIBUICAO",
    "imposto_retido": "IMPOSTO",
    "decimo_terceiro": "DECIMO_TERCEIRO",
    "irrf_decimo_terceiro": "IRRF_DECIMO_TERCEIRO",
}
CAMPOS_JSON = {"cnpj_cpf": "NI_PAGADOR", "nome": "NOME_PAGADOR", **VALORES}
# RendPJTitular.verificaValores: pendência (erro) se estes quatro estão todos em branco.
OBRIGATORIO_ALGUM_VALOR = ("rendimentos", "contribuicao_previdenciaria", "decimo_terceiro", "imposto_retido")

# --- validação ---

def validar_item(item: dict, cpf_declarante: str | None) -> tuple[dict, list[str]]:
    """Campos do Registro21 já convertidos e os erros. As mensagens não repetem os dados."""
    campos, erros = {}, []
    if not isinstance(item, dict):
        return campos, ["esperado um objeto com os campos da fonte pagadora"]
    for chave in sorted(set(item) - set(CAMPOS_JSON) - {referencia.CAMPO}):
        erros.append(f"campo desconhecido '{chave}'")
    for chave in CAMPOS_JSON:
        if item.get(chave) is None or str(item[chave]).strip() == "":
            erros.append(f"campo obrigatório '{chave}' não informado")
    erros += referencia.validar(item, REF)

    if item.get("cnpj_cpf"):
        ni = so_digitos(item["cnpj_cpf"])
        if not ni_valido(ni):
            erros.append("'cnpj_cpf': CPF (11 dígitos) ou CNPJ (14 dígitos) inválido")
        elif ni == cpf_declarante:
            erros.append("'cnpj_cpf': a fonte pagadora não pode ser o próprio declarante")
        else:
            campos["NI_PAGADOR"] = ni

    if item.get("nome") and str(item["nome"]).strip():
        nome = normalizar_texto(str(item["nome"]))
        fora = caracteres_fora_do_latin1(nome.upper())
        if fora:
            erros.append(f"'nome': caractere(s) não aceito(s) pelo programa: {', '.join(repr(c) for c in fora)}")
        elif len(nome) > Registro21.NOME_PAGADOR.tamanho:
            erros.append(f"'nome': tem {len(nome)} caracteres; o máximo é {Registro21.NOME_PAGADOR.tamanho}")
        else:
            campos["NOME_PAGADOR"] = nome

    for chave, nome_campo in VALORES.items():
        if item.get(chave) is None or str(item[chave]).strip() == "":
            continue
        try:
            valor = valor_em_reais(item[chave])
            getattr(Registro21, nome_campo).formatar(valor)
            campos[nome_campo] = valor
        except ValueError as erro:
            erros.append(f"'{chave}': {erro}")

    principais = [VALORES[chave] for chave in OBRIGATORIO_ALGUM_VALOR]
    if all(nome in campos for nome in principais) and all(campos[nome] == 0 for nome in principais):
        erros.append("rendimentos, contribuição previdenciária, 13º salário e imposto retido estão todos "
                     "zerados (o programa acusa erro \"Faltam valores\")")
    return campos, erros

def validar(itens: list[dict], cpf_declarante: str | None = None) -> tuple[list[dict], list[str]]:
    campos_por_item, erros = [], []
    for numero, item in enumerate(itens, start=1):
        campos, erros_item = validar_item(item, cpf_declarante)
        campos_por_item.append(campos)
        erros.extend(f"fonte {numero}: {erro}" for erro in erros_item)
    return campos_por_item, erros

# --- gravação ---

def montar_linha(campos: dict, cpf: str) -> str:
    linha = Registro21.linha_vazia()
    linha = Registro21.TIPO_REGISTRO.gravar(linha, 21)
    linha = Registro21.CPF.gravar(linha, cpf)
    for nome, valor in campos.items():
        linha = getattr(Registro21, nome).gravar(linha, valor)
    return Registro21.gravar_cod_controle(linha)        # sempre por último

def sem_valores(linha: str) -> bool:
    return all(int(getattr(Registro21, nome).ler(linha)) == 0 for nome in VALORES.values())

def preencher_linha(linha: str, campos: dict) -> str:
    """Fonte sem valores no DBK: grava os valores do JSON (e o nome, se estiver em branco)."""
    for nome in VALORES.values():
        linha = getattr(Registro21, nome).gravar(linha, campos[nome])
    if not Registro21.NOME_PAGADOR.ler(linha).strip():
        linha = Registro21.NOME_PAGADOR.gravar(linha, campos["NOME_PAGADOR"])
    return Registro21.gravar_cod_controle(linha)

@dataclass
class Resultado:
    """Fontes do JSON pelo número (a partir de 1); fontes do DBK pela ordem na ficha (a partir de 1)."""
    preenchidas: list[int] = field(default_factory=list)          # fonte sem valores no DBK, preenchida
    novas: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)
    por_referencia: list[int] = field(default_factory=list)       # achadas pelo campo "dbk", não pela busca
    dbk_sem_valores: list[int] = field(default_factory=list)      # continuam sem valores: erro no programa
    dbk_nao_informadas: list[int] = field(default_factory=list)   # com valores, não vieram no JSON

def inserir(arquivo: ArquivoDBK, itens: list[dict], campos_por_item: list[dict]) -> Resultado:
    resultado = Resultado()
    da_entrada = len(arquivo.indices(Registro21.TIPO))     # as novas entram depois das linhas da entrada
    cpf = arquivo.cpf_declarante
    usadas = set()                                          # ordem (1...) das fontes do DBK preenchidas
    referencias = [referencia.numero(item, REF) for item in itens]
    # Fontes do JSON com o mesmo CPF/CNPJ, entre as que dependem da busca (com "dbk", cada uma indica o seu item).
    repetidos = Counter(campos["NI_PAGADOR"] for campos, ref in zip(campos_por_item, referencias) if not ref)
    referenciadas = {ref for ref in referencias if ref}
    repetidas = referencia.repetidas(itens, REF)

    def fontes_da_entrada() -> list[int]:
        return arquivo.indices(Registro21.TIPO)[:da_entrada]

    for numero, campos in enumerate(campos_por_item, start=1):
        descricao = f"Fonte {numero}"
        ni = campos["NI_PAGADOR"]
        ref = referencias[numero - 1]
        if ref:                                             # docs/adr/0027: a referência substitui a busca
            problema = None
            if numero in repetidas:
                problema = "outra fonte do JSON indica a mesma fonte do DBK"
            elif ref > len(fontes_da_entrada()):
                problema = "a fonte indicada em 'dbk' não existe no DBK"
            else:
                ni_dbk = Registro21.NI_PAGADOR.ler(arquivo.linhas[fontes_da_entrada()[ref - 1]]).strip()
                if ni_dbk and ni_dbk != ni:
                    problema = "a fonte indicada em 'dbk' tem outro CPF/CNPJ"
            if problema:
                logger.warning("%s: %s; não foi gravada (revisão).", descricao, problema)
                resultado.revisao.append(numero)
                continue
            encontradas = [(ref, fontes_da_entrada()[ref - 1])]
            resultado.por_referencia.append(numero)
        else:
            encontradas = [(ordem, posicao) for ordem, posicao in enumerate(fontes_da_entrada(), start=1)
                           if Registro21.NI_PAGADOR.ler(arquivo.linhas[posicao]).strip() == ni]
            if any(ordem in referenciadas for ordem, _ in encontradas):
                logger.warning("%s: a fonte do DBK com esse CPF/CNPJ foi indicada em 'dbk' por outra fonte do "
                               "JSON; não foi gravada (revisão).", descricao)
                resultado.revisao.append(numero)
                continue

        usadas.update(ordem for ordem, _ in encontradas)     # veio no JSON, mesmo que vá para revisão
        if len(encontradas) > 1:
            logger.warning("%s: %d fontes no DBK com o mesmo CPF/CNPJ; não foi gravada (revisão).", descricao, len(encontradas))
            resultado.revisao.append(numero)
            continue
        if encontradas:
            ordem, posicao = encontradas[0]
            if not sem_valores(arquivo.linhas[posicao]):
                logger.warning("%s: a fonte já tem valores no DBK; não foi gravada (revisão).", descricao)
                resultado.revisao.append(numero)
                continue
            if repetidos[ni] > 1:
                logger.warning("%s: outra fonte do JSON tem o mesmo CPF/CNPJ e o DBK tem só uma; "
                               "não foi gravada (revisão).", descricao)
                resultado.revisao.append(numero)
                continue
            arquivo.substituir(posicao, preencher_linha(arquivo.linhas[posicao], campos))
            usadas.add(ordem)
            logger.info("%s: valores gravados na fonte sem valores do DBK (linha %d)", descricao, posicao + 1)
            resultado.preenchidas.append(numero)
            continue

        if repetidos[ni] > 1:
            logger.warning("%s: outra fonte do JSON tem o mesmo CPF/CNPJ; as duas são lançadas.", descricao)
        posicao = arquivo.inserir(Registro21.TIPO, montar_linha(campos, cpf))
        logger.info("%s inserida na linha %d", descricao, posicao + 1)
        resultado.novas.append(numero)

    for ordem, posicao in enumerate(fontes_da_entrada(), start=1):
        if sem_valores(arquivo.linhas[posicao]):                 # inclusive a que foi para revisão
            resultado.dbk_sem_valores.append(ordem)
        elif ordem not in usadas:
            resultado.dbk_nao_informadas.append(ordem)
    return resultado

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Fontes do DBK no formato do JSON de entrada, com a ordem na ficha em "dbk" (docs/adr/0026)."""
    itens = []
    for ordem, linha in enumerate(arquivo.linhas_do_tipo(Registro21.TIPO), start=1):
        item = {"cnpj_cpf": Registro21.NI_PAGADOR.ler(linha).strip(),
                "nome": Registro21.NOME_PAGADOR.ler(linha).strip()}
        for chave, nome in VALORES.items():
            item[chave] = numero_do_dbk(getattr(Registro21, nome).ler(linha))
        item["dbk"] = {"item": ordem}
        itens.append(item)
    return itens

def relatorio(resultado: Resultado) -> list[tuple[int, str]]:
    def numeros(lista: list[int]) -> str:
        return ", ".join(map(str, lista))

    linhas = [(logging.INFO, f"{NOME}: {len(resultado.preenchidas)} preenchida(s), {len(resultado.novas)} nova(s), "
                             f"{len(resultado.revisao)} para revisão")]
    if resultado.preenchidas:
        linhas.append((logging.INFO, f"  preenchidas (fontes sem valores do DBK; fontes do JSON): {numeros(resultado.preenchidas)}"))
    if resultado.novas:
        linhas.append((logging.INFO, f"  lançadas como novas (fontes do JSON): {numeros(resultado.novas)}"))
    if resultado.por_referencia:
        linhas.append((logging.INFO, "  achadas pela referência 'dbk', não pela busca (fontes do JSON): "
                                     f"{numeros(resultado.por_referencia)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, f"  REVISÃO, não gravadas (fontes do JSON): {numeros(resultado.revisao)}"))
    if resultado.dbk_sem_valores:
        linhas.append((logging.WARNING, "  REVISÃO, fontes do DBK que continuam sem valores (o programa acusa erro "
                                        f"\"Faltam valores\"; itens da ficha): {numeros(resultado.dbk_sem_valores)}"))
    if resultado.dbk_nao_informadas:
        linhas.append((logging.WARNING, "  REVISÃO, fontes do DBK com valores que não vieram no JSON (itens da "
                                        f"ficha): {numeros(resultado.dbk_nao_informadas)}"))
    return linhas
