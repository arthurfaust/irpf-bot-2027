# 0012. Bloco `bolsa` com a pergunta "Negociados em Bolsa?" obrigatória

- **Status:** Aceito (substitui em parte o 0008: "Negociado em bolsa?" deixa de ter padrão "Não")
- **Data:** 16/11/2026

## Contexto

O ADR 0008 deixou "Negociado em bolsa?" sem exigência, com o padrão "Não" (`IN_BOLSA` = 0). A leitura
do programa IRPF 2026 mostrou que:

- `Bem$32` exige a resposta a "Negociados em Bolsa" nos bens em que ela aparece (`isBemNegociadoBolsa`:
  ações 03/01, ativos negociados em bolsa 04/04 e quase todos os fundos do grupo 07), com nível
  **erro**: em branco, a declaração não pode ser entregue.
- `Bem$33` exige o código de negociação, também como erro, quando a resposta é "1" (sim).
- O campo da tela tem 13 caracteres (`Alfa` de 13), embora `NR_COD_NEGOCIACAO_BOLSA` tenha 20 no DBK.
- O DBK não tem valor para "não respondido": `IN_BOLSA` 0 = não, 1 = sim. O bot gravava 0 em todos
  esses bens, ou seja, respondia "Não" sem o JSON ter dito nada.
- Um DBK gravado pelo programa em 16/11/2026 com 6 bens (`tests/dados/bolsa_programa.DBK`) confirmou o
  formato: o bot gera linhas idênticas byte a byte.

## Decisão

- Bloco `bolsa` no JSON: `negociado` (true/false) e `codigo`.
- `negociado` é obrigatório nos bens em que o programa faz a pergunta; `codigo` é obrigatório quando
  `negociado` é true e não se aplica quando é false.
- O código só aceita letras e números, até 13 caracteres, e é gravado em maiúsculas.

## Alternativas consideradas

- Manter o padrão "Não": uma ação listada sem o bloco seria gravada como não negociada, sem aviso.
- Deduzir "negociado" da presença do código: esconde a omissão quando a IA esquece os dois.

## Consequências

- JSON com ação, BDR/opção ou fundo do grupo 07 (exceto 01 e 05) sem o bloco `bolsa` passa a ser
  recusado na validação.
- A busca de ações (CNPJ + código de negociação) é o passo seguinte.
