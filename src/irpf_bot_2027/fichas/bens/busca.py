"""
Procura, no DBK, o lançamento que corresponde a um bem do JSON.

O DBK de entrada é a cópia de segurança com a declaração do ano anterior importada, então a maior
parte dos bens já existe e só precisa da situação atual. A busca usa uma chave por tipo de bem
(decisões em docs/adr/0006 e 0007):

    | Bem                                        | Chave                                          |
    |--------------------------------------------|------------------------------------------------|
    | Fundos nacionais (grupo 07, exceto 99)     | grupo + CNPJ do fundo                          |
    | Cripto 08/01-03, autocustodiante           | grupo + código + ativo + "AUTO"                |
    | Cripto 08/01-03, custodiado no Brasil      | grupo + código + ativo + CNPJ do custodiante   |
    | Cripto custodiado no exterior, NFT, outros | sem busca: lançamento novo                     |
    | Demais                                     | sem busca: lançamento novo                     |

"Ativo" é a sigla da altcoin (08/02) ou da stablecoin (08/03); vazio no bitcoin (08/01).

Um bem de tipo com busca cujos campos da chave estão vazios no DBK (ex.: cripto de uma declaração
antiga, sem custodiante) tem "chave incompleta": não é encontrado por nenhum bem do JSON, e o bem
do JSON do mesmo tipo vai para revisão em vez de ser lançado em duplicidade (ficha.py).

Origem:
    - Fundos: os códigos de CNPJ_OBRIGATORIO["07"] (regras da tela), então todo fundo nacional
      gravado pelo programa tem o CNPJ preenchido.
    - Cripto: CRIPTO_COM_CUSTODIANTE e o campo CNPJ só no Brasil (regras da tela); campos
      AUTOCUSTODIANTE, ALTCOIN e STABLECOIN do registro 27.
    - A escolha das chaves é do projeto.
"""

from dataclasses import dataclass

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import BRASIL, CNPJ_OBRIGATORIO, Registro27, esta_na_tabela

GRUPO_FUNDOS = "07"
GRUPO_CRIPTO = "08"
CAMPO_DO_ATIVO = {"01": None, "02": "ALTCOIN", "03": "STABLECOIN"}    # cripto com busca: código -> campo

@dataclass(frozen=True)
class Identificacao:
    tipo: tuple          # bens do mesmo tipo (ex.: ("08", "01")): usado para achar chaves incompletas
    chave: tuple | None  # chave completa, ou None se algum campo dela está vazio

def identificar(campos: dict) -> Identificacao | None:
    """Identificação do bem (campos do JSON já validados ou lidos de uma linha 27 com
    Registro27.ler_tudo), ou None se o tipo não tem busca."""
    grupo, codigo, pais = campos.get("GRUPO"), campos.get("CODIGO"), campos.get("PAIS")
    cnpj = campos.get("CNPJ_CPF", "")

    if grupo == GRUPO_FUNDOS and esta_na_tabela(CNPJ_OBRIGATORIO, grupo, codigo) and pais == BRASIL:
        return Identificacao((grupo,), (grupo, cnpj) if cnpj else None)

    if grupo == GRUPO_CRIPTO and codigo in CAMPO_DO_ATIVO:
        campo_ativo = CAMPO_DO_ATIVO[codigo]
        ativo = str(campos.get(campo_ativo, "")).strip().upper() if campo_ativo else ""
        tipo = (grupo, codigo)
        if campo_ativo and not ativo:
            return Identificacao(tipo, None)
        if str(campos.get("AUTOCUSTODIANTE", "")) == "1":
            return Identificacao(tipo, (grupo, codigo, ativo, "AUTO"))
        if pais != BRASIL:
            return None                                      # custodiado no exterior: não há CNPJ
        return Identificacao(tipo, (grupo, codigo, ativo, cnpj) if cnpj else None)

    return None

def chave_busca(campos: dict) -> tuple | None:
    """Chave completa do bem, ou None (tipo sem busca ou chave incompleta)."""
    identificacao = identificar(campos)
    return identificacao.chave if identificacao else None

def identificar_linha(linha: str) -> Identificacao | None:
    return identificar(Registro27.ler_tudo(linha))

def procurar(arquivo: ArquivoDBK, chave: tuple) -> list[int]:
    """Posições (a partir de 0) das linhas 27 do DBK com a chave."""
    return [i for i in arquivo.indices(Registro27.TIPO) if chave_busca(Registro27.ler_tudo(arquivo.linhas[i])) == chave]

def procurar_incompletos(arquivo: ArquivoDBK, tipo: tuple) -> list[int]:
    """Posições das linhas 27 do DBK do mesmo tipo, mas com a chave incompleta."""
    posicoes = []
    for i in arquivo.indices(Registro27.TIPO):
        identificacao = identificar_linha(arquivo.linhas[i])
        if identificacao and identificacao.tipo == tipo and identificacao.chave is None:
            posicoes.append(i)
    return posicoes
