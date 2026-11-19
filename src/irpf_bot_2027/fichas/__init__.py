"""
Fichas da declaração que o bot sabe preencher.

Cada ficha é um subpacote que expõe:
    NOME        nome da ficha no programa (para os logs)
    CHAVE_JSON  nome da lista no JSON do cliente (ex.: "bens")
    validar(itens, cpf_declarante) -> (dados_validados, erros)
    inserir(arquivo, itens, dados_validados) -> resultado (o que foi gravado e o que ficou para revisão)
    relatorio(resultado) -> [(nível de log, texto)], sem dados do cliente
    exportar(arquivo) -> [itens do DBK no formato do JSON de entrada, com a referência em "dbk"]
                         (docs/adr/0026; a ida e volta é testada em tests/test_exportacao.py)

Para acrescentar uma ficha: criar o subpacote com essa forma e incluí-lo em FICHAS.
A ordem de FICHAS é a ordem em que elas são validadas e inseridas.
"""

from irpf_bot_2027.fichas import alimentandos, bens, dependentes, pagamentos, rendimentos_pj

# dependentes antes de alimentandos ("Alimentando do" pode ser um dependente) e os dois antes de
# pagamentos: quem é novo pode receber pagamentos na mesma execução.
FICHAS = (rendimentos_pj, dependentes, alimentandos, pagamentos, bens)

# Chaves do JSON que não são de nenhuma ficha, mas são esperadas (não geram aviso).
CHAVES_JSON_CONHECIDAS = {"cpf"}
