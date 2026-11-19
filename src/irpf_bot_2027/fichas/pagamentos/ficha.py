"""
Ficha Pagamentos Efetuados (registro 26): montagem, inserção e relatório.

Os outros módulos: validacao.py (JSON -> campos), busca.py (chave e dependente/alimentando no DBK),
exportacao.py (DBK -> JSON).

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

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import referencia
from irpf_bot_2027.fichas.pagamentos.busca import VALORES, chave_busca, sem_valores, vinculado_no_dbk
from irpf_bot_2027.fichas.pagamentos.exportacao import exportar
from irpf_bot_2027.fichas.pagamentos.validacao import CPF, TIPOS_JSON, validar, validar_item
from irpf_bot_2027.leiautes.atual import Registro25, Registro26, Registro35
from irpf_bot_2027.leiautes.atual import tabela_pagamentos as tabela

logger = logging.getLogger(__name__)

NOME = "Pagamentos Efetuados"
CHAVE_JSON = "pagamentos"
REF = "item"                        # "dbk": {"item": N}, a ordem do pagamento na ficha do DBK (docs/adr/0027)

__all__ = ["CHAVE_JSON", "NOME", "exportar", "inserir", "relatorio", "validar", "validar_item",
           "vinculado_no_dbk", "completar", "montar_linha", "sem_valores"]

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
    por_referencia: list[int] = field(default_factory=list)     # achados pelo campo "dbk", não pela busca
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

    referencias = [referencia.numero(item, REF) for item in itens]
    repetidas = referencia.repetidas(itens, REF)
    referenciados = {ref for ref in referencias if ref}
    # Pagamentos do JSON com a mesma chave, entre os que dependem da busca (com "dbk", cada um indica o seu).
    repetidos = Counter(chave_busca(linha) for numero, linha in linhas_completas.items() if not referencias[numero - 1])
    usados = set()                                          # ordem (1...) dos pagamentos do DBK encontrados

    for numero, linha in linhas_completas.items():
        descricao = f"Pagamento {numero}"
        chave = chave_busca(linha)
        ref = referencias[numero - 1]
        if ref:                                             # docs/adr/0027: a referência substitui a busca
            problema = None
            if numero in repetidas:
                problema = "outro pagamento do JSON indica o mesmo pagamento do DBK"
            elif ref > len(entrada):
                problema = "o pagamento indicado em 'dbk' não existe no DBK"
            else:
                no_dbk = arquivo.linhas[entrada[ref - 1]]
                mesmos = all(campo.ler(no_dbk) == campo.ler(linha) for campo in
                             (Registro26.CODIGO, Registro26.TIPO_PAGAMENTO, Registro26.CHAVE_DEPENDENTE))
                ni_dbk, ni_json = (Registro26.NI_BENEFICIARIO.ler(l).strip() for l in (no_dbk, linha))
                if not mesmos:
                    problema = "o pagamento indicado em 'dbk' tem outro código, tipo ou dependente/alimentando"
                elif ni_dbk and ni_json and ni_dbk != ni_json:
                    problema = "o pagamento indicado em 'dbk' tem outro CPF/CNPJ do beneficiário"
            if problema:
                logger.warning("%s: %s; não foi gravado (revisão).", descricao, problema)
                resultado.revisao.append(numero)
                continue
            encontrados = [(ref, entrada[ref - 1])]
            resultado.por_referencia.append(numero)
        else:
            encontrados = [(ordem, posicao) for ordem, posicao in enumerate(entrada, start=1)
                           if chave_busca(arquivo.linhas[posicao]) == chave]
            if any(ordem in referenciados for ordem, _ in encontrados):
                logger.warning("%s: o pagamento do DBK com a mesma chave foi indicado em 'dbk' por outro pagamento "
                               "do JSON; não foi gravado (revisão).", descricao)
                resultado.revisao.append(numero)
                continue
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
    if resultado.por_referencia:
        linhas.append((logging.INFO, "  achados pela referência 'dbk', não pela busca (pagamentos do JSON): "
                                     f"{numeros(resultado.por_referencia)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, "  REVISÃO, não gravados: já existiam no DBK ou a referência 'dbk' não "
                                        f"conferiu, veja os avisos acima (pagamentos do JSON): {numeros(resultado.revisao)}"))
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
