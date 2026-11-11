"""
Ficha Bens e Direitos: validar e inserir os bens do JSON no DBK (registro 27).

Duas etapas, sempre nesta ordem e para a lista inteira:
    1. validar(bens): confere todos os bens e devolve os erros. Se houver qualquer erro,
       nada deve ser inserido.
    2. inserir(arquivo, bens, campos_por_bem): atualiza o lançamento existente (quando o tipo de bem
       tem busca e ele é encontrado) ou monta uma linha 27 nova e insere no arquivo.

Origem: não tem regras próprias; usa o leiaute em uso (leiautes/atual.py), a validação
(validacao.py) e a busca (busca.py).
"""

import logging
from collections import Counter
from dataclasses import dataclass, field

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas.bens.busca import chave_busca, procurar, tem_busca
from irpf_bot_2027.fichas.bens.entrada import CAMPOS_SIMPLES
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.atual import BRASIL, TITULAR_OU_DEPENDENTE, Registro27, esta_na_tabela, nome_codigo

logger = logging.getLogger(__name__)

NOME = "Bens e Direitos"            # nome da ficha no programa, usado nos logs
CHAVE_JSON = "bens"                 # nome da lista no JSON do cliente

def validar(bens: list[dict]) -> tuple[list[dict], list[str]]:
    """Valida todos os bens.

    Returns:
        - campos de cada bem vindos do JSON, já convertidos (mesma ordem da lista de entrada);
        - erros de todos os bens, cada um com o número do bem ("bem 2: ...").
    """
    campos_por_bem = []
    erros = []
    for numero, bem in enumerate(bens, start=1):
        campos, erros_bem = validar_bem(bem)
        campos_por_bem.append(campos)
        erros.extend(f"bem {numero}: {erro}" for erro in erros_bem)
    return campos_por_bem, erros

def proxima_chave(arquivo: ArquivoDBK) -> int:
    """Maior chave de bem existente + 1 (ou 1, se o DBK não tiver bens)."""
    chaves = [int(Registro27.CHAVE.ler(linha)) for linha in arquivo.linhas_do_tipo(Registro27.TIPO)]
    return max(chaves, default=0) + 1

def montar_linha(bem: dict, campos: dict, cpf: str, chave: int) -> str:
    """Linha 27 completa de um bem já validado, com o código de controle.

    campos: todos os campos vindos do JSON, já convertidos (validacao.validar_bem).
    Aqui só se acrescentam os campos calculados: padrões, EXTERIOR e CHAVE.
    """
    exterior = 0 if campos["PAIS"] == BRASIL else 1
    tem_titular_dependente = esta_na_tabela(TITULAR_OU_DEPENDENTE, bem["grupo"], bem["codigo"])

    linha = Registro27.gravar_valores_padrao(cpf, tem_titular_dependente)
    linha = Registro27.EXTERIOR.gravar(linha, exterior)
    linha = Registro27.CHAVE.gravar(linha, chave)

    for nome, valor in campos.items():
        linha = getattr(Registro27, nome).gravar(linha, valor)

    return Registro27.gravar_cod_controle(linha)       # sempre por último

def atualizar_linha(linha: str, campos: dict) -> str:
    """Linha 27 existente com a situação atual do JSON. Nada mais muda: VALOR_ANTERIOR vem da
    declaração anterior e nunca é alterado."""
    linha = Registro27.VALOR_ATUAL.gravar(linha, campos["VALOR_ATUAL"])
    return Registro27.gravar_cod_controle(linha)       # sempre por último

@dataclass
class BemDoDBK:
    """Bem que já estava no DBK de entrada, identificado sem dados do cliente."""
    chave: int                  # CHAVE do registro 27 (número do bem no programa)
    grupo: str
    codigo: str
    com_busca: bool             # o tipo tem busca automática (busca.py)

    def descrever(self) -> str:
        return f"chave {self.chave} ({self.grupo}/{self.codigo}, {nome_codigo(self.grupo, self.codigo)})"

@dataclass
class Resultado:
    """O que inserir() fez. Bens do JSON pelo número (a partir de 1); bens do DBK por BemDoDBK."""
    atualizados: list[int] = field(default_factory=list)
    novos: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)              # não gravados: decisão humana
    nao_informados: list[BemDoDBK] = field(default_factory=list)  # no DBK, não atualizados pelo JSON

def bem_do_dbk(linha: str) -> BemDoDBK:
    lido = Registro27.ler_tudo(linha)
    return BemDoDBK(int(lido["CHAVE"]), lido["GRUPO"], lido["CODIGO"], tem_busca(lido["GRUPO"], lido["CODIGO"], lido["PAIS"]))

def inserir(arquivo: ArquivoDBK, bens: list[dict], campos_por_bem: list[dict]) -> Resultado:
    """Grava os bens (já validados) no arquivo, na ordem do JSON.

    Para cada bem com chave de busca (busca.py), procura o lançamento no DBK:
        1 encontrado  -> atualiza só a situação atual;
        0 encontrados -> lançamento completo, com chave nova (como os bens sem busca);
        2 ou mais     -> não grava nada desse bem; vai para revisão.
    Se dois bens do JSON têm a mesma chave e ela existe no DBK, os dois vão para revisão.
    Os bens que já estavam no DBK e não foram atualizados vão para Resultado.nao_informados;
    nunca são zerados nem apagados.
    """
    resultado = Resultado()
    chave = proxima_chave(arquivo)
    cpf = arquivo.cpf_declarante
    chaves_json = Counter(filter(None, map(chave_busca, campos_por_bem)))
    existentes = [bem_do_dbk(linha) for linha in arquivo.linhas_do_tipo(Registro27.TIPO)]
    chaves_atualizadas = set()                  # CHAVE dos bens do DBK atualizados

    for numero, (bem, campos) in enumerate(zip(bens, campos_por_bem), start=1):
        descricao = f"Bem {numero} ({bem['grupo']}/{bem['codigo']}, {nome_codigo(bem['grupo'], bem['codigo'])})"
        chave_bem = chave_busca(campos)
        encontrados = procurar(arquivo, chave_bem) if chave_bem else []

        if len(encontrados) > 1:
            logger.warning("%s: %d lançamentos no DBK com a mesma chave; não foi gravado (revisão).",
                           descricao, len(encontrados))
            resultado.revisao.append(numero)
            continue

        if encontrados and chaves_json[chave_bem] > 1:
            # Dois bens do JSON apontando para o mesmo lançamento: um sobrescreveria o outro.
            logger.warning("%s: outro bem do JSON tem a mesma chave e o DBK tem um lançamento com ela; "
                           "não foi gravado (revisão).", descricao)
            resultado.revisao.append(numero)
            continue

        if len(encontrados) == 1:
            posicao = encontrados[0]
            linha = arquivo.linhas[posicao]
            if Registro27.VALOR_ANTERIOR.formatar(campos["VALOR_ANTERIOR"]) != Registro27.VALOR_ANTERIOR.ler(linha):
                logger.warning("%s: a situação anterior do JSON difere da do DBK; mantida a do DBK.", descricao)
            arquivo.substituir(posicao, atualizar_linha(linha, campos))
            chaves_atualizadas.add(int(Registro27.CHAVE.ler(linha)))
            logger.info("%s: situação atual atualizada na linha %d", descricao, posicao + 1)
            resultado.atualizados.append(numero)
            continue

        posicao = arquivo.inserir(Registro27.TIPO, montar_linha(bem, campos, cpf, chave))
        logger.info("%s inserido na linha %d com chave %d", descricao, posicao + 1, chave)
        extras = sorted(set(campos) - set(CAMPOS_SIMPLES.values()))      # só os campos dos blocos
        logger.info("  campos extras gravados: %s", ", ".join(extras) or "nenhum")
        resultado.novos.append(numero)
        chave += 1

    resultado.nao_informados = [bem for bem in existentes if bem.chave not in chaves_atualizadas]
    return resultado

def relatorio(resultado: Resultado) -> list[tuple[int, str]]:
    """Linhas do relatório da execução, como (nível de log, texto). Sem dados do cliente:
    os bens do JSON aparecem pelo número; os do DBK, pela chave e pelo tipo."""
    def numeros(lista: list[int]) -> str:
        return ", ".join(map(str, lista))

    linhas = [(logging.INFO, f"{NOME}: {len(resultado.atualizados)} atualizado(s), {len(resultado.novos)} "
                             f"novo(s), {len(resultado.revisao)} para revisão, {len(resultado.nao_informados)} "
                             f"do DBK sem atualização")]
    if resultado.atualizados:
        linhas.append((logging.INFO, f"  atualizados (bens do JSON): {numeros(resultado.atualizados)}"))
    if resultado.novos:
        linhas.append((logging.INFO, f"  lançados como novos (bens do JSON): {numeros(resultado.novos)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, f"  REVISÃO, não gravados (bens do JSON): {numeros(resultado.revisao)}"))
    if resultado.nao_informados:
        linhas.append((logging.WARNING, "  REVISÃO, bens do DBK que o JSON não atualizou (nada foi zerado "
                                        "nem apagado; a situação atual continua a do DBK):"))
        for bem in resultado.nao_informados:
            aviso = "" if bem.com_busca else " - tipo sem busca automática: confira se o JSON não o lançou de novo"
            linhas.append((logging.WARNING, f"    {bem.descrever()}{aviso}"))
    return linhas
