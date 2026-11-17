"""
Procura, no DBK, o lançamento que corresponde a um bem do JSON.

O DBK de entrada é a cópia de segurança com a declaração do ano anterior importada, então a maior
parte dos bens já existe e só precisa da situação atual. A busca usa uma chave por tipo de bem
(decisões em docs/adr/0006, 0007, 0011, 0013 e 0015):

    | Bem                                        | Chave                                          |
    |--------------------------------------------|------------------------------------------------|
    | Veículo, aeronave, embarcação (02/01-03)   | grupo + código + país + registro (***)         |
    | Ações no Brasil (03/01)                    | grupo + código + CNPJ + código de negociação   |
    |                                            | (vazio se não é negociada em bolsa) (**)       |
    | Ativos negociados em bolsa (04/04)         | grupo + código + código de negociação          |
    | Fundos nacionais (grupo 07, exceto 99)     | grupo + CNPJ do fundo                          |
    | Poupança (04/01) e conta corrente (06/01)  | grupo + código + banco + agência + conta (*)   |
    | Cripto 08/01-03, autocustodiante           | grupo + código + ativo + "AUTO"                |
    | Cripto 08/01-03, custodiado no Brasil      | grupo + código + ativo + CNPJ do custodiante   |
    | Cripto custodiado no exterior, NFT, outros | sem busca: lançamento novo                     |
    | Demais                                     | sem busca: lançamento novo                     |

"Ativo" é a sigla da altcoin (08/02) ou da stablecoin (08/03); vazio no bitcoin (08/01).
(*) Banco, agência e conta sem zeros à esquerda: a mesma conta da Caixa aparece com 12 dígitos no DBK
gravado pelo programa e pode voltar sem os zeros. O grupo e o código entram porque, em vários
bancos, a poupança tem o mesmo número da conta corrente (confirmado no DBK do programa de 13/11/2026).
(**) O código de negociação separa ON e PN da mesma empresa. Ação do JSON não encontrada, com outra
ação do mesmo CNPJ no DBK ("família"), vai para revisão: pode ser a mesma ação declarada antes sem o
código ou com outro código.
(***) Registro (Renavam, registro estrangeiro do veículo, de aeronave ou de embarcação) em maiúsculas,
só com letras e números e sem zeros à esquerda: o programa completa com zeros o registro do veículo
(ADR 0014), e o mesmo registro pode ter sido digitado com ou sem hífen.

Um bem de tipo com busca cujos campos da chave estão vazios no DBK (ex.: cripto de uma declaração
antiga, sem custodiante) tem "chave incompleta": não é encontrado por nenhum bem do JSON, e o bem
do JSON do mesmo tipo vai para revisão em vez de ser lançado em duplicidade (ficha.py).

Origem:
    - Fundos: os códigos de CNPJ_OBRIGATORIO["07"] (regras da tela), então todo fundo nacional
      gravado pelo programa tem o CNPJ preenchido.
    - Contas: CONTA_BANCARIA (regras da tela), só no Brasil; campos BANCO, AGENCIA e CONTA.
    - Veículo, aeronave e embarcação: REGISTRO_BEM_MOVEL (regras da tela); campos RENAVAM,
      REG_AERONAVE e REG_EMBARCACAO do registro 27.
    - Ações e 04/04: CNPJ_OBRIGATORIO["03"] e TEM_CNPJ_CPF (04/04 não tem CNPJ); campos BOLSA e
      COD_NEGOCIACAO do registro 27 (ADR 0012).
    - Cripto: CRIPTO_COM_CUSTODIANTE e o campo CNPJ só no Brasil (regras da tela); campos
      AUTOCUSTODIANTE, ALTCOIN e STABLECOIN do registro 27.
    - A escolha das chaves é do projeto.
"""

from dataclasses import dataclass

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import (
    BRASIL, CNPJ_OBRIGATORIO, CONTA_BANCARIA, REGISTRO_BEM_MOVEL, Registro27, esta_na_tabela,
)

GRUPO_FUNDOS = "07"
GRUPO_CRIPTO = "08"
CAMPO_DO_ATIVO = {"01": None, "02": "ALTCOIN", "03": "STABLECOIN"}    # cripto com busca: código -> campo

GRUPO_BENS_MOVEIS = "02"
ACOES = ("03", "01")
ATIVOS_EM_BOLSA = ("04", "04")                                        # BDRs, opções e outros (sem CNPJ)

@dataclass(frozen=True)
class Identificacao:
    tipo: tuple          # bens do mesmo tipo (ex.: ("08", "01")): usado para achar chaves incompletas
    chave: tuple | None  # chave completa, ou None se algum campo dela está vazio
    familia: tuple | None = None    # bens que podem ser o mesmo apesar da chave diferente (ações: mesmo CNPJ)

def identificar_acao(grupo: str, codigo: str, campos: dict) -> Identificacao:
    """Ação no Brasil: CNPJ + código de negociação (vazio se não é negociada em bolsa)."""
    cnpj = campos.get("CNPJ_CPF", "")
    negociado = str(campos.get("BOLSA", "")) == "1"
    cod = str(campos.get("COD_NEGOCIACAO", "")).strip().upper()
    if not cnpj or (negociado and not cod):
        return Identificacao((grupo, codigo), None)
    return Identificacao((grupo, codigo), (grupo, codigo, cnpj, cod if negociado else ""), familia=(grupo, codigo, cnpj))

def sem_zeros_a_esquerda(texto) -> str:
    """"0567" -> "567"; "000" -> "" (campo numérico não preenchido no DBK)."""
    return str(texto or "").strip().lstrip("0")

def chave_da_conta(grupo: str, codigo: str, campos: dict) -> tuple | None:
    """grupo + código + banco + agência + conta, sem zeros à esquerda; None se algum está vazio ou se
    a conta do DBK tem algo além de dígitos (ex.: "12345-6", digitada com o DV numa declaração antiga)."""
    banco, agencia, conta = (sem_zeros_a_esquerda(campos.get(nome)) for nome in ("BANCO", "AGENCIA", "CONTA"))
    if not (banco and agencia and conta) or not conta.isdigit():
        return None
    return (grupo, codigo, banco, agencia, conta)

def normalizar_registro(valor) -> str:
    """"0ABC1234-FL" -> "ABC1234FL"; "00987654322" -> "987654322"; "pt-abc" -> "PTABC"."""
    return "".join(c for c in str(valor or "").upper() if c.isalnum()).lstrip("0")

def identificar(campos: dict) -> Identificacao | None:
    """Identificação do bem (campos do JSON já validados ou lidos de uma linha 27 com
    Registro27.ler_tudo), ou None se o tipo não tem busca."""
    grupo, codigo, pais = campos.get("GRUPO"), campos.get("CODIGO"), campos.get("PAIS")
    cnpj = campos.get("CNPJ_CPF", "")

    if grupo == GRUPO_FUNDOS and esta_na_tabela(CNPJ_OBRIGATORIO, grupo, codigo) and pais == BRASIL:
        return Identificacao((grupo,), (grupo, cnpj) if cnpj else None)

    if grupo == GRUPO_BENS_MOVEIS and codigo in REGISTRO_BEM_MOVEL:
        registro = normalizar_registro(campos.get(REGISTRO_BEM_MOVEL[codigo]))
        tipo = (grupo, codigo, pais)                         # o país separa os tipos: no exterior o registro é opcional
        return Identificacao(tipo, (grupo, codigo, pais, registro) if registro else None)

    if (grupo, codigo) == ACOES and pais == BRASIL:
        return identificar_acao(grupo, codigo, campos)

    if (grupo, codigo) == ATIVOS_EM_BOLSA and pais == BRASIL:
        if str(campos.get("BOLSA", "")) != "1":
            return None                                      # sem código de negociação não há o que comparar
        cod = str(campos.get("COD_NEGOCIACAO", "")).strip().upper()
        return Identificacao((grupo, codigo), (grupo, codigo, cod) if cod else None)

    if esta_na_tabela(CONTA_BANCARIA, grupo, codigo) and pais == BRASIL:
        return Identificacao((grupo, codigo), chave_da_conta(grupo, codigo, campos))

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

def procurar_semelhantes(arquivo: ArquivoDBK, identificacao: Identificacao) -> list[int]:
    """Posições das linhas 27 da mesma família (ex.: ação com o mesmo CNPJ), mas com outra chave."""
    if identificacao.familia is None:
        return []
    posicoes = []
    for i in arquivo.indices(Registro27.TIPO):
        outra = identificar_linha(arquivo.linhas[i])
        if outra and outra.familia == identificacao.familia and outra.chave != identificacao.chave:
            posicoes.append(i)
    return posicoes

def procurar_incompletos(arquivo: ArquivoDBK, tipo: tuple) -> list[int]:
    """Posições das linhas 27 do DBK do mesmo tipo, mas com a chave incompleta."""
    posicoes = []
    for i in arquivo.indices(Registro27.TIPO):
        identificacao = identificar_linha(arquivo.linhas[i])
        if identificacao and identificacao.tipo == tipo and identificacao.chave is None:
            posicoes.append(i)
    return posicoes
