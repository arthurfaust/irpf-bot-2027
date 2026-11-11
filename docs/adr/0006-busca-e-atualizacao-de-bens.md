# 0006. Procurar o bem no DBK e atualizar em vez de lançar

- **Status:** Aceito
- **Data:** 11/11/2026

## Contexto

O DBK de entrada é a cópia de segurança com a declaração do ano anterior importada: a maior parte dos
bens já existe, com a situação anterior preenchida, e só falta a situação atual. Lançar tudo de novo
duplicaria os bens. Bens, dívidas e dependentes passam de um ano para outro; rendimentos não.

## Decisão

- Cada tipo de bem com busca tem uma chave (`fichas/bens/busca.py`). Para cada bem do JSON:
  **1** lançamento com a chave → atualiza só a situação atual (`VALOR_ATUAL`) e o controle;
  **0** → lançamento completo, com chave nova; **2 ou mais** → não grava e vai para revisão.
- `VALOR_ANTERIOR` de um bem existente nunca é alterado; se o JSON trouxer outro valor, sai um aviso.
  Discriminação e demais campos do DBK também não mudam (por enquanto).
- Dois bens do JSON com a mesma chave que existe no DBK vão os dois para revisão.
- Bens do DBK que o JSON não atualizou entram numa lista de revisão; nunca são zerados nem apagados.
- O relatório no fim da execução mostra atualizados, novos, revisão e não atualizados, sem dados do
  cliente.
- Primeiro tipo: fundos nacionais (grupo 07 com CNPJ obrigatório), chave grupo + CNPJ. O código do
  bem não entra na chave. Confirmado no programa em 11/11/2026 (`tests/manual/fundos/`).
- A busca é opção de cada ficha (rendimentos sempre lançam).

## Alternativas consideradas

- Começar por conta corrente/poupança (chave mais confiável): dependia do bloco `conta` (fase 4).
- Imóvel (IPTU/matrícula): campos muitas vezes vazios ou com outra formatação em declarações antigas,
  o que levaria a lançamentos em duplicidade.
- Ações sem código de negociação: ON e PN da mesma empresa dariam ambiguidade.

## Consequências

- O operador precisa ler a parte de revisão do relatório a cada execução.
- Tipos sem busca continuam sendo lançados como novos; o relatório pede para conferir duplicidade.
