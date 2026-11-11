"""
Procura, no DBK, o lançamento que corresponde a um bem do JSON.

O DBK de entrada é a cópia de segurança com a declaração do ano anterior importada, então a maior
parte dos bens já existe e só precisa da situação atual. A busca usa uma chave por tipo de bem:

    | Bem                                      | Chave                 |
    |------------------------------------------|-----------------------|
    | Fundos nacionais (grupo 07, exceto 99)   | grupo + CNPJ do fundo |
    | Demais                                   | sem busca: lançamento novo |

Origem:
    - Os códigos de fundos nacionais são os de CNPJ_OBRIGATORIO["07"] (leiautes, regras da tela),
      então todo fundo nacional gravado pelo programa tem o CNPJ preenchido.
    - A escolha das chaves é do projeto (docs/plano.md, fase 3). O código do bem não entra na
      chave: um fundo com o mesmo CNPJ é o mesmo bem, ainda que o JSON traga outro código.
"""

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import BRASIL, CNPJ_OBRIGATORIO, Registro27, esta_na_tabela

GRUPO_FUNDOS = "07"

def chave_busca(campos: dict) -> tuple[str, str] | None:
    """Chave de identificação do bem (campos já validados), ou None se o tipo não tem busca."""
    grupo, codigo = campos.get("GRUPO"), campos.get("CODIGO")
    if (grupo == GRUPO_FUNDOS and esta_na_tabela(CNPJ_OBRIGATORIO, grupo, codigo)
            and campos.get("PAIS") == BRASIL):
        cnpj = campos.get("CNPJ_CPF", "")
        return (grupo, cnpj) if cnpj else None
    return None

def chave_da_linha(linha: str) -> tuple[str, str]:
    """A mesma chave, lida de uma linha 27 do DBK."""
    lido = Registro27.ler_tudo(linha)
    return lido["GRUPO"], lido["CNPJ_CPF"]

def procurar(arquivo: ArquivoDBK, chave: tuple[str, str]) -> list[int]:
    """Posições (a partir de 0) das linhas 27 do DBK com a chave."""
    return [i for i in arquivo.indices(Registro27.TIPO) if chave_da_linha(arquivo.linhas[i]) == chave]
