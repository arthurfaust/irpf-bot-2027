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

def tem_busca(grupo: str, codigo: str, pais: str) -> bool:
    """True se o tipo de bem tem busca automática no DBK."""
    return grupo == GRUPO_FUNDOS and esta_na_tabela(CNPJ_OBRIGATORIO, grupo, codigo) and pais == BRASIL

def chave_busca(campos: dict) -> tuple[str, str] | None:
    """Chave de identificação do bem (campos do JSON já validados ou campos lidos de uma linha 27
    com Registro27.ler_tudo), ou None se o tipo não tem busca ou o campo da chave está vazio."""
    grupo, codigo, pais = campos.get("GRUPO"), campos.get("CODIGO"), campos.get("PAIS")
    cnpj = campos.get("CNPJ_CPF", "")
    return (grupo, cnpj) if tem_busca(grupo, codigo, pais) and cnpj else None

def chave_da_linha(linha: str) -> tuple[str, str] | None:
    """A mesma chave, lida de uma linha 27 do DBK."""
    return chave_busca(Registro27.ler_tudo(linha))

def procurar(arquivo: ArquivoDBK, chave: tuple[str, str]) -> list[int]:
    """Posições (a partir de 0) das linhas 27 do DBK com a chave."""
    return [i for i in arquivo.indices(Registro27.TIPO) if chave_da_linha(arquivo.linhas[i]) == chave]
