"""
Ficha Alimentandos (registro 35): montagem, busca pelo CPF, inserção e relatório.

Os outros módulos: validacao.py (JSON -> campos) e exportacao.py (DBK -> JSON).

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
from dataclasses import dataclass, field

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas.alimentandos.exportacao import exportar
from irpf_bot_2027.fichas.alimentandos.validacao import BLOCOS, validar, validar_item
from irpf_bot_2027.leiautes.atual import Registro25, Registro35

logger = logging.getLogger(__name__)

NOME = "Alimentandos"
CHAVE_JSON = "alimentandos"

__all__ = ["CHAVE_JSON", "NOME", "exportar", "inserir", "relatorio", "validar", "validar_item", "montar_linha"]

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
