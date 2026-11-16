# 0011. Chave da busca de poupança e conta corrente

- **Status:** Aceito (complementa 0006 e 0007)
- **Data:** 16/11/2026

## Contexto

Com o bloco `conta` (ADR 0010), poupança (04/01) e conta corrente ou conta pagamento (06/01) passam a
ser lançadas e precisam de busca, como fundos e cripto. O que se sabe:

- No DBK gravado pelo programa em 13/11/2026 (`tests/dados/contas_programa.DBK`), a poupança e a
  conta corrente do Itaú têm banco, agência e conta idênticos.
- A conta da Caixa é gravada com 12 dígitos e zeros à esquerda, mas a restauração joga o `NR_CONTA`
  inteiro no campo conta; a mesma conta pode reaparecer com outra quantidade de zeros. A agência é
  numérica (zeros à esquerda no DBK) e no JSON pode vir sem eles.
- O campo conta do programa é texto: numa declaração antiga, a conta pode ter sido digitada com o DV
  ("12345-6"), o que não bate com a conta só com números do JSON.

## Decisão

- Chave: grupo + código + banco + agência + conta, os três últimos sem zeros à esquerda. O DV e o
  CNPJ da instituição não entram.
- Só no Brasil (o programa só mostra os campos de conta no Brasil).
- Banco, agência ou conta em branco, ou conta com algo além de dígitos no DBK = chave incompleta
  (ADR 0007): o bem do JSON do mesmo grupo/código sem correspondente vai para revisão.

## Alternativas consideradas

- Só banco + agência + conta: a poupança atualizaria a conta corrente do mesmo número.
- Incluir o DV: um DV corrigido de um ano para o outro faria a conta virar um lançamento novo.
- Tirar os caracteres não numéricos da conta do DBK: "12345-6" viraria "123456", que não é a conta;
  melhor mandar para revisão.

## Consequências

- Conta antiga da Caixa: se o JSON trouxer a operação na frente e o DBK não (ou o contrário), as duas
  não casam; o bem do JSON é lançado como novo e a conta do DBK aparece no relatório como não
  atualizada. O teste `test_conta_da_caixa_com_operacao_no_json_nao_casa_com_a_do_dbk_sem_operacao`
  documenta essa limitação.
