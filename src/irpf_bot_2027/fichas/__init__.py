"""
Fichas da declaração que o bot sabe preencher.

Cada ficha é um subpacote que expõe:
    NOME        nome da ficha no programa (para os logs)
    CHAVE_JSON  nome da lista no JSON do cliente (ex.: "bens")
    validar(itens) -> (dados_validados, erros)
    inserir(arquivo, itens, dados_validados) -> resultado (o que foi gravado e o que ficou para revisão)
    relatorio(resultado) -> [(nível de log, texto)], sem dados do cliente

Para acrescentar uma ficha: criar o subpacote com essa forma e incluí-lo em FICHAS.
A ordem de FICHAS é a ordem em que elas são validadas e inseridas.
"""

from irpf_bot_2027.fichas import bens

FICHAS = (bens,)

# Chaves do JSON que não são de nenhuma ficha, mas são esperadas (não geram aviso).
CHAVES_JSON_CONHECIDAS = {"cpf"}
