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
from irpf_bot_2027.fichas.bens.busca import (
    chave_busca, identificar, procurar, procurar_incompletos, procurar_semelhantes,
)
from irpf_bot_2027.fichas.bens.entrada import CAMPOS_SIMPLES
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.fichas.bens.entrada import origem_no_json
from irpf_bot_2027.leiautes.atual import (
    BRASIL, TITULAR_OU_DEPENDENTE, Registro27, campos_aplicaveis, esta_na_tabela, nome_codigo,
)

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

# --- atualização de um bem encontrado (docs/adr/0016) ---

# Tipos em que a discriminação traz a quantidade, que muda todo ano: a do JSON substitui a do DBK.
# Escolha do projeto (ADR 0016): ações, BDRs/opções, fundos e criptoativos.
DISCRIMINACAO_DO_JSON = {("03", "01"), ("04", "04")}
GRUPOS_DISCRIMINACAO_DO_JSON = {"07", "08"}

# Indicadores sim/não: 0 é a resposta "Não", não um campo vazio.
INDICADORES = {"BOLSA", "USUFRUTO", "AUTOCUSTODIANTE", "CONTA_PAGAMENTO"}
# Indicadores cujo "não informado" é 2 (leiaute: NM_IND_REG_IMOV e NM_UNID).
NAO_INFORMADO = {"REGISTRADO_CARTORIO": "2", "UNIDADE_AREA": "2"}
# Valores do ano no exterior (ADR 0017): como a situação atual, sempre os do JSON quando informados.
VALORES_DO_ANO = {"AF_RENDIMENTO", "AF_IMPOSTO", "LD_RECEBIDO", "LD_IMPOSTO"}
# Tratados à parte: situação atual (gravada), situação anterior (nunca muda), discriminação (regra acima).
TRATADOS_A_PARTE = {"VALOR_ATUAL", "VALOR_ANTERIOR", "DISCRIMINACAO"} | VALORES_DO_ANO
# Nunca preenchidos nem trocados; diferença só gera aviso.
SO_AVISAR = {"GRUPO", "CODIGO", "PAIS"}

def discriminacao_do_json(grupo: str, codigo: str) -> bool:
    return grupo in GRUPOS_DISCRIMINACAO_DO_JSON or (grupo, codigo) in DISCRIMINACAO_DO_JSON

def vazio_no_dbk(nome: str, texto: str) -> bool:
    if nome in NAO_INFORMADO:
        return texto == NAO_INFORMADO[nome]
    if nome in INDICADORES:
        return False
    if getattr(Registro27, nome).tipo == "N":
        return texto.strip("0") == ""
    return texto.strip() == ""

def equivalentes(nome: str, gravado_pelo_json: str, no_dbk: str) -> bool:
    """Mesmo valor, ignorando o formato: números pelo valor; textos em maiúsculas, só letras e números,
    sem zeros à esquerda (ex.: conta "000000004321" = "4321", "PT-ABC" = "PTABC")."""
    if getattr(Registro27, nome).tipo == "N":
        return int(gravado_pelo_json) == int(no_dbk)
    def normalizar(texto: str) -> str:
        return "".join(c for c in texto.upper() if c.isalnum()).lstrip("0")
    return normalizar(gravado_pelo_json) == normalizar(no_dbk)

def mesmo_texto(a: str, b: str) -> bool:
    return " ".join(a.upper().split()) == " ".join(b.upper().split())

@dataclass
class Atualizacao:
    """O que atualizar_linha mudou ou encontrou de diferente (nomes de campos do Registro27)."""
    linha: str
    preenchidos: list[str] = field(default_factory=list)    # estavam em branco no DBK
    diferentes: list[str] = field(default_factory=list)     # preenchidos e diferentes: mantido o do DBK
    discriminacao_substituida: bool = False
    valores_do_ano: list[str] = field(default_factory=list)  # valores do exterior gravados (diferentes do DBK)

def atualizar_linha(linha: str, campos: dict) -> Atualizacao:
    """Linha 27 existente atualizada com o bem do JSON.

    - VALOR_ATUAL: sempre o do JSON. VALOR_ANTERIOR: nunca muda (vem da declaração anterior).
    - DISCRIMINACAO: a do JSON nos tipos em que a quantidade muda todo ano (discriminacao_do_json);
      nos demais, a do DBK, e a diferença vai para `diferentes`.
    - Valores do ano no exterior (VALORES_DO_ANO): os do JSON, quando informados (ADR 0017).
    - Grupo, código e país: nunca mudam; diferença vai para `diferentes`.
    - Demais campos do JSON que a tela mostra para o bem do DBK: em branco no DBK, recebem o valor do
      JSON; preenchidos e diferentes, ficam como estão e vão para `diferentes`.
    """
    lido = Registro27.ler_tudo(linha)
    atualizacao = Atualizacao(linha)
    linha = Registro27.VALOR_ATUAL.gravar(linha, campos["VALOR_ATUAL"])

    if not mesmo_texto(campos["DISCRIMINACAO"], lido["DISCRIMINACAO"]):
        if discriminacao_do_json(lido["GRUPO"], lido["CODIGO"]):
            linha = Registro27.DISCRIMINACAO.gravar(linha, campos["DISCRIMINACAO"])
            atualizacao.discriminacao_substituida = True
        else:
            atualizacao.diferentes.append("DISCRIMINACAO")

    aplicaveis = campos_aplicaveis(lido["GRUPO"], lido["CODIGO"], lido["PAIS"],
                                   autocustodiante=lido["AUTOCUSTODIANTE"] == "1", bolsa=lido["BOLSA"] == "1")
    for nome in sorted(VALORES_DO_ANO & set(campos) & aplicaveis):
        campo = getattr(Registro27, nome)
        if campo.formatar(campos[nome]) != campo.ler(linha):
            linha = campo.gravar(linha, campos[nome])
            atualizacao.valores_do_ano.append(nome)

    for nome, valor in campos.items():
        if nome in TRATADOS_A_PARTE or (nome not in SO_AVISAR and nome not in aplicaveis):
            continue
        campo = getattr(Registro27, nome)
        gravado, no_dbk = campo.formatar(valor), campo.ler(linha)
        if equivalentes(nome, gravado, no_dbk):
            continue
        if nome not in SO_AVISAR and vazio_no_dbk(nome, no_dbk):
            linha = campo.gravar(linha, valor)
            atualizacao.preenchidos.append(nome)
        else:
            atualizacao.diferentes.append(nome)

    atualizacao.linha = Registro27.gravar_cod_controle(linha)       # sempre por último
    return atualizacao

@dataclass
class BemDoDBK:
    """Bem que já estava no DBK de entrada, identificado sem dados do cliente."""
    chave: int                  # CHAVE do registro 27 (número do bem no programa)
    grupo: str
    codigo: str
    com_busca: bool             # tem chave completa: um bem do JSON o encontraria (busca.py)
    chave_incompleta: bool = False   # o tipo tem busca, mas falta algum campo da chave no DBK

    def descrever(self) -> str:
        return f"chave {self.chave} ({self.grupo}/{self.codigo}, {nome_codigo(self.grupo, self.codigo)})"

@dataclass
class Resultado:
    """O que inserir() fez. Bens do JSON pelo número (a partir de 1); bens do DBK por BemDoDBK."""
    atualizados: list[int] = field(default_factory=list)
    novos: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)              # não gravados: decisão humana
    conferir: list[int] = field(default_factory=list)             # atualizados com campo diferente do DBK
    nao_informados: list[BemDoDBK] = field(default_factory=list)  # no DBK, não atualizados pelo JSON

def bem_do_dbk(linha: str) -> BemDoDBK:
    lido = Registro27.ler_tudo(linha)
    identificacao = identificar(lido)
    com_busca = bool(identificacao and identificacao.chave)
    return BemDoDBK(int(lido["CHAVE"]), lido["GRUPO"], lido["CODIGO"], com_busca,
                    chave_incompleta=bool(identificacao) and not com_busca)

def inserir(arquivo: ArquivoDBK, bens: list[dict], campos_por_bem: list[dict]) -> Resultado:
    """Grava os bens (já validados) no arquivo, na ordem do JSON.

    Para cada bem com chave de busca (busca.py), procura o lançamento no DBK:
        1 encontrado  -> atualiza a situação atual e completa o lançamento (atualizar_linha, ADR 0016);
        0 encontrados -> lançamento completo, com chave nova (como os bens sem busca);
        2 ou mais     -> não grava nada desse bem; vai para revisão.
    A busca olha só os bens do DBK de entrada, nunca os lançados nesta mesma execução.
    Se dois bens do JSON têm a mesma chave e ela existe no DBK, os dois vão para revisão; se ela não
    existe, os dois são lançados, com aviso.
    Se nada foi encontrado, mas o DBK tem bem do mesmo tipo com a chave incompleta, o bem do JSON
    vai para revisão (pode ser o mesmo bem; lançá-lo criaria duplicidade). O mesmo vale para uma
    ação não encontrada quando o DBK tem outra ação do mesmo CNPJ (outro código de negociação ou sem ele).
    Os bens que já estavam no DBK e não foram atualizados vão para Resultado.nao_informados;
    nunca são zerados nem apagados.
    """
    resultado = Resultado()
    chave = proxima_chave(arquivo)
    primeira_chave_nova = chave                 # bens com CHAVE a partir daqui foram lançados nesta execução
    cpf = arquivo.cpf_declarante
    chaves_json = Counter(filter(None, map(chave_busca, campos_por_bem)))
    existentes = [bem_do_dbk(linha) for linha in arquivo.linhas_do_tipo(Registro27.TIPO)]
    chaves_atualizadas = set()                  # CHAVE dos bens do DBK atualizados

    def da_entrada(posicoes: list[int]) -> list[int]:
        """Só as linhas que já estavam no DBK de entrada: um bem lançado nesta execução não pode ser
        encontrado (nem sobrescrito) por outro bem do mesmo JSON."""
        return [p for p in posicoes if int(Registro27.CHAVE.ler(arquivo.linhas[p])) < primeira_chave_nova]

    for numero, (bem, campos) in enumerate(zip(bens, campos_por_bem), start=1):
        descricao = f"Bem {numero} ({bem['grupo']}/{bem['codigo']}, {nome_codigo(bem['grupo'], bem['codigo'])})"
        chave_bem = chave_busca(campos)
        encontrados = da_entrada(procurar(arquivo, chave_bem)) if chave_bem else []

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
            conferir = []
            if Registro27.VALOR_ANTERIOR.formatar(campos["VALOR_ANTERIOR"]) != Registro27.VALOR_ANTERIOR.ler(linha):
                logger.warning("%s: a situação anterior do JSON difere da do DBK; mantida a do DBK.", descricao)
                conferir.append("situacao_anterior")
            atualizacao = atualizar_linha(linha, campos)
            arquivo.substituir(posicao, atualizacao.linha)
            chaves_atualizadas.add(int(Registro27.CHAVE.ler(linha)))
            logger.info("%s: situação atual atualizada na linha %d", descricao, posicao + 1)
            if atualizacao.discriminacao_substituida:
                logger.info("  discriminação substituída pela do JSON")
            if atualizacao.valores_do_ano:
                logger.info("  valores do ano no exterior gravados: %s",
                            ", ".join(origem_no_json(bem, n) or n for n in atualizacao.valores_do_ano))
            if atualizacao.preenchidos:
                logger.info("  preenchidos (estavam em branco no DBK): %s",
                            ", ".join(origem_no_json(bem, n) or n for n in atualizacao.preenchidos))
            if atualizacao.diferentes:
                nomes = [origem_no_json(bem, n) or n for n in atualizacao.diferentes]
                logger.warning("%s: diferente do DBK, mantido o do DBK: %s", descricao, ", ".join(nomes))
                conferir += nomes
            if conferir:
                resultado.conferir.append(numero)
            resultado.atualizados.append(numero)
            continue

        if chave_bem and da_entrada(procurar_incompletos(arquivo, identificar(campos).tipo)):
            logger.warning("%s: não encontrado, mas o DBK tem bem do mesmo tipo com dados da chave em branco ou fora do formato; "
                           "não foi gravado (revisão).", descricao)
            resultado.revisao.append(numero)
            continue

        if chave_bem and da_entrada(procurar_semelhantes(arquivo, identificar(campos))):
            logger.warning("%s: não encontrado, mas o DBK tem bem do mesmo tipo e CNPJ com outro código de "
                           "negociação (ou sem ele); não foi gravado (revisão).", descricao)
            resultado.revisao.append(numero)
            continue

        if chave_bem and chaves_json[chave_bem] > 1:
            logger.warning("%s: outro bem do JSON tem a mesma chave; os dois são lançados como novos, mas "
                           "na próxima declaração cairão em revisão (2 lançamentos com a mesma chave).", descricao)

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
    if resultado.conferir:
        linhas.append((logging.WARNING, "  CONFERIR, atualizados com campo diferente do DBK (mantido o do DBK; "
                                        f"veja os avisos acima) (bens do JSON): {numeros(resultado.conferir)}"))
    if resultado.nao_informados:
        linhas.append((logging.WARNING, "  REVISÃO, bens do DBK que o JSON não atualizou (nada foi zerado "
                                        "nem apagado; a situação atual continua a do DBK):"))
        for bem in resultado.nao_informados:
            if bem.com_busca:
                aviso = ""
            elif bem.chave_incompleta:
                aviso = " - dados da chave em branco ou fora do formato no DBK: confira e complete no programa"
            else:
                aviso = " - tipo sem busca automática: confira se o JSON não o lançou de novo"
            linhas.append((logging.WARNING, f"    {bem.descrever()}{aviso}"))
    return linhas
