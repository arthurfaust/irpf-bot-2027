"""
Ficha Bens e Direitos: validar e inserir os bens do JSON no DBK (registro 27).

Duas etapas, sempre nesta ordem e para a lista inteira:
    1. validar(bens): confere todos os bens e devolve os erros. Se houver qualquer erro,
       nada deve ser inserido.
    2. inserir(arquivo, bens, campos_por_bem): monta uma linha 27 por bem e insere no arquivo.

Origem: não tem regras próprias; usa o leiaute em uso (leiautes/atual.py) e a validação (validacao.py).
"""

import logging

from irpf_bot_2027.dbk import ArquivoDBK
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
    exterior = 0 if str(bem["pais"]) == BRASIL else 1
    tem_titular_dependente = esta_na_tabela(TITULAR_OU_DEPENDENTE, bem["grupo"], bem["codigo"])

    linha = Registro27.gravar_valores_padrao(cpf, tem_titular_dependente)
    linha = Registro27.EXTERIOR.gravar(linha, exterior)
    linha = Registro27.CHAVE.gravar(linha, chave)

    for nome, valor in campos.items():
        linha = getattr(Registro27, nome).gravar(linha, valor)

    return Registro27.gravar_cod_controle(linha)       # sempre por último

def inserir(arquivo: ArquivoDBK, bens: list[dict], campos_por_bem: list[dict]) -> None:
    """Insere os bens (já validados) no arquivo, com chaves novas e na ordem do JSON."""
    chave = proxima_chave(arquivo)
    cpf = arquivo.cpf_declarante

    for bem, campos in zip(bens, campos_por_bem):
        posicao = arquivo.inserir(Registro27.TIPO, montar_linha(bem, campos, cpf, chave))
        logger.info("Bem %s/%s (%s) inserido na linha %d com chave %d", bem["grupo"], bem["codigo"], nome_codigo(bem["grupo"], bem["codigo"]), posicao + 1, chave)
        extras = sorted(set(campos) - set(CAMPOS_SIMPLES.values()))      # só os campos dos blocos
        logger.info("  campos extras gravados: %s", ", ".join(extras) or "nenhum")
        chave += 1
