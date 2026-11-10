"""
Ficha Bens e Direitos: validar e inserir os bens do JSON no DBK (registro 27).

Duas etapas, sempre nesta ordem e para a lista inteira:
    1. validar(bens): confere todos os bens e devolve os erros. Se houver qualquer erro,
       nada deve ser inserido.
    2. inserir(arquivo, bens, campos_por_bem): monta uma linha 27 por bem e insere no arquivo.

Origem: não tem regras próprias; usa o leiaute (leiautes/irpf2026) e a validação (validacao.py).
"""

import logging

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas.bens.validacao import validar_bem
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27
from irpf_bot_2027.leiautes.irpf2026.regras import BRASIL, TITULAR_OU_DEPENDENTE, esta_na_tabela
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import nome_codigo

logger = logging.getLogger(__name__)

CHAVE_JSON = "bens"                 # nome da lista no JSON do cliente

def validar(bens: list[dict]) -> tuple[list[dict], list[str]]:
    """Valida todos os bens.

    Returns:
        - campos extras de cada bem, já convertidos (mesma ordem da lista de entrada);
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
    """Linha 27 completa de um bem já validado, com o código de controle."""
    exterior = 0 if str(bem["pais"]) == BRASIL else 1
    tem_titular_dependente = esta_na_tabela(TITULAR_OU_DEPENDENTE, bem["grupo"], bem["codigo"])

    linha = Registro27.gravar_valores_padrao(cpf, tem_titular_dependente)
    linha = Registro27.GRUPO.gravar(linha, bem["grupo"])
    linha = Registro27.CODIGO.gravar(linha, bem["codigo"])
    linha = Registro27.PAIS.gravar(linha, bem["pais"])
    linha = Registro27.EXTERIOR.gravar(linha, exterior)
    linha = Registro27.DISCRIMINACAO.gravar(linha, bem["discriminacao"])
    linha = Registro27.VALOR_ANTERIOR.gravar(linha, bem["situacao_anterior"])
    linha = Registro27.VALOR_ATUAL.gravar(linha, bem["situacao_atual"])
    linha = Registro27.USUFRUTO.gravar(linha, bem.get("usufruto", False))
    linha = Registro27.CHAVE.gravar(linha, chave)

    for nome, valor in campos.items():                 # campos dos blocos do JSON, já validados
        linha = getattr(Registro27, nome).gravar(linha, valor)

    return Registro27.gravar_cod_controle(linha)       # sempre por último

def inserir(arquivo: ArquivoDBK, bens: list[dict], campos_por_bem: list[dict]) -> None:
    """Insere os bens (já validados) no arquivo, com chaves novas e na ordem do JSON."""
    chave = proxima_chave(arquivo)
    cpf = arquivo.cpf_declarante

    for bem, campos in zip(bens, campos_por_bem):
        posicao = arquivo.inserir(Registro27.TIPO, montar_linha(bem, campos, cpf, chave))
        logger.info("Bem %s/%s (%s) inserido na linha %d com chave %d", bem["grupo"], bem["codigo"],
                    nome_codigo(bem["grupo"], bem["codigo"]), posicao + 1, chave)
        logger.info("  campos extras gravados: %s", ", ".join(sorted(campos)) or "nenhum")
        chave += 1
