# 0010. Bloco `conta` libera poupança e conta corrente

- **Status:** Aceito (substitui em parte o 0008: conta corrente e poupança deixam de ser barradas)
- **Data:** 13/11/2026

## Contexto

Poupança (04/01) e conta corrente ou conta pagamento (06/01) no Brasil exigem banco, agência, conta e
DV, que o JSON não tinha (ADR 0008). O que se sabe do programa IRPF 2026:

- `Bem` tem validadores de "não nulo" para banco, agência, conta e DV (`Bem$16` a `$19`), todos com
  nível **aviso**, e confere o DV pelo algoritmo de cada banco (`ValidadorDvContaCorrente`, também aviso).
- O banco vem de `lib/resources/bancos_bens.xml` (651 bancos).
- A tela de bens **não tem** o campo Operação da Caixa. `Bem.getContaFormatadaTxt` grava a conta da
  Caixa sem operação com 12 dígitos (zeros à esquerda); os demais bancos, como digitada.
- Na restauração, o `NR_CONTA` inteiro vai para o campo conta (`ConversorRegistros2ObjetosIRPF`).
- Um DBK gravado pelo programa em 13/11/2026 com 6 contas (`tests/dados/contas_programa.DBK`)
  confirmou o formato: o bot gera linhas idênticas byte a byte.

## Decisão

- Bloco `conta` no JSON: `banco`, `agencia`, `conta`, `dv` (obrigatórios) e `conta_pagamento`
  (opcional, só 06/01). O CNPJ da instituição continua em `cnpj_cpf`, como nos fundos.
- Os quatro obrigatórios são exigidos pelo bot, embora o programa só avise: banco, agência e conta
  formam a chave da busca, e o DV completa o que o programa pede.
- Agência e conta só com números (o DV vai separado); o banco precisa existir na tabela do programa.
- Na Caixa, a conta é completada com zeros até 12 dígitos, como o programa grava. Não há campo
  `operacao`: quem tem conta antiga com operação informa operação + conta em `conta`.
- O DV não é conferido pelo algoritmo do banco: o programa mostra o aviso.

## Alternativas consideradas

- Campo `operacao` para a Caixa: a tela de bens não tem esse campo, e o DBK do programa não o separa.
- Conferir o DV pelo algoritmo de cada banco: cerca de 20 algoritmos para repetir um aviso que o
  programa já dá.
- DV opcional: o programa o trata como os outros três; deixá-lo em branco só geraria pendência.

## Consequências

- Poupança e conta corrente passam a ser lançadas. A busca por banco + agência + conta é o passo
  seguinte; até lá elas aparecem no relatório como "tipo sem busca automática".
- A busca terá de comparar a conta sem zeros à esquerda: a mesma conta da Caixa pode vir com ou sem
  os zeros (restauração do DBK) e com ou sem a operação na frente.
