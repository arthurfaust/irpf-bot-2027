# 0022. Pagamentos inseridos na ordem do código

- **Status:** Aceito
- **Data:** 18/11/2026
- **Substitui em parte:** 0021 (posição da linha nova)

## Contexto

O ADR 0021 deixou a linha nova de pagamento depois do último pagamento do DBK, sem ordenar, e pediu a
confirmação no roteiro manual. No roteiro de 18/11/2026 (`tests/manual/pagamentos/`), o programa
restaurou as saídas do bot sem erro e regravou as mesmas linhas 26, mas **ordenadas pelo código**;
dentro do mesmo código, manteve a ordem em que estavam (o 10 do titular, que já existia, antes do 10
do dependente, lançado depois).

O relatório cita os pagamentos do DBK pela ordem no arquivo ("itens da ficha"). Com a saída do bot
fora de ordem, esses números não batiam com a numeração da tela.

## Decisão

- O pagamento novo entra depois do último pagamento do DBK com código menor ou igual ao dele; sem
  nenhum, antes do primeiro pagamento. É a ordem em que o programa regrava.
- `ArquivoDBK.inserir` ganha o parâmetro opcional `ordenar_por` (função da linha para o valor de
  ordenação); sem ele, continua inserindo depois da última linha do tipo.

## Alternativas consideradas

- Reordenar todas as linhas 26 do DBK: mexeria em linhas que o bot não lançou e mudaria a numeração de
  um DBK de entrada fora de ordem.
- Deixar como estava: o programa corrige a ordem, mas o relatório da execução citaria itens errados.

## Consequências

- A saída do bot passa a ter as linhas 26 na mesma ordem do DBK regravado pelo programa (confirmado
  nos dois testes do roteiro).
- As outras fichas continuam inserindo no fim; se outro registro também for gravado ordenado, basta
  passar `ordenar_por`.
