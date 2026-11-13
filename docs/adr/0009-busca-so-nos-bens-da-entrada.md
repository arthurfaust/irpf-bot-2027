# 0009. A busca olha só os bens do DBK de entrada

- **Status:** Aceito (complementa 0006)
- **Data:** 13/11/2026

## Contexto

No teste manual de 13/11/2026 com um DBK sem bens, dois bens do JSON com a mesma chave (o mesmo fundo
ou o mesmo ETH na mesma corretora) não tiveram o mesmo tratamento: o 1º foi lançado e o 2º foi para
revisão, porque a busca do 2º encontrou a linha que o 1º tinha acabado de inserir. Pior: se o 2º
fosse único na sua chave, ele atualizaria o lançamento recém-criado e sobrescreveria o valor do 1º.
O ADR 0006 só tratava a chave repetida quando ela já existe no DBK.

## Decisão

- A busca considera só os bens que estavam no DBK de entrada (CHAVE menor que a primeira chave nova
  desta execução). Um bem lançado na execução nunca é encontrado nem atualizado por outro bem do JSON.
- Chave repetida no JSON e **existente** no DBK: os dois vão para revisão (como no 0006).
- Chave repetida no JSON e **ausente** do DBK: os dois são lançados como novos, com um aviso de que
  na próxima declaração cairão em revisão (dois lançamentos com a mesma chave).

## Alternativas consideradas

- Mandar para revisão também quando a chave não está no DBK: bloquearia o caso legítimo do mesmo
  fundo em duas corretoras declarado em dois itens.

## Consequências

- O resultado de cada bem do JSON não depende da ordem dos bens no JSON.
- Itens duplicados por engano da IA chegam ao DBK; o aviso no log é a defesa nesse caso.
