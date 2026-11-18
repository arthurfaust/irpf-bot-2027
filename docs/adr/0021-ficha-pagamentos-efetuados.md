# 0021. Ficha Pagamentos Efetuados

- **Status:** Aceito; substituído em parte por 0022 (posição da linha nova)
- **Data:** 18/11/2026

## Contexto

Terceira ficha do bot (registro 26, 671 posições). Cada pagamento tem código, CPF/CNPJ e nome do
beneficiário, valor pago, parcela não dedutível/reembolsada, descrição, país e, quando é de dependente
ou alimentando, a chave dele (registros 25 e 35).

Do programa IRPF 2026 (`tipoPagamentos.xml` e classes `Pagamento` e `PainelPagamentosDetalhe`, lidas
com `javap`; detalhes em `leiautes/irpf2026/tabela_pagamentos.py`):

- Cada código mostra campos diferentes: os do exterior não têm CPF/CNPJ e exigem o país; a pensão não
  tem tipo nem nome (o alimentando vem da lista); advogados, profissionais liberais, aluguéis e
  arrendamento não têm a pergunta titular/dependente/alimentando nem parcela não dedutível; 36, 37 e 99
  aceitam só titular ou dependente.
- CPF obrigatório (09 a 14, 66), CNPJ obrigatório (01, 21, 26, 36, 37), CPF ou CNPJ obrigatório (60 a
  62, 70 a 76), opcional no 99. O beneficiário não pode ser o declarante nem o dependente/alimentando.
- Parcela não dedutível maior que o valor pago: erro. Descrição obrigatória só no 99.
- O programa procura o dependente/alimentando pelo nome; o DBK guarda a chave dele.
- Os códigos de doação (40 a 47, 80, 81) estão na mesma tabela, mas a tela de pagamentos esconde todos
  os campos com eles.

Um DBK gravado pelo programa em 18/11/2026 com 8 pagamentos, um dependente e uma alimentanda
(`tests/dados/pagamentos_programa.DBK`) mostrou: tipo do CPF/CNPJ 1 ou 2 (0 sem ele), tipo do
pagamento em branco nos códigos sem a pergunta e "A" na pensão, CPF e nome da alimentanda gravados no
pagamento de pensão, país 000 no Brasil e os pagamentos ordenados pelo código.

## Decisão

- Lista `pagamentos` no JSON: `codigo`, `tipo` ("T", "D" ou "A", como `pertence_a` dos bens),
  `cpf_dependente_alimentando`, `cnpj_cpf`, `nome`, `valor_pago`, `parcela_nao_dedutivel`, `descricao`,
  `pais`. O bot aceita só os campos que a tela mostra para o código e exige os que ela exige; além
  disso, exige nome e valor pago maior que zero (escolha do projeto).
- Dependente e alimentando são indicados pelo CPF e procurados nos registros 25 e 35 do DBK. Sem eles,
  o pagamento vai para revisão sem ser gravado, até existir a ficha de dependentes.
- Na pensão, o CPF e o nome do beneficiário vêm do alimentando do DBK, como o programa grava.
- Busca no DBK de entrada pela chave código + tipo + dependente/alimentando + CPF/CNPJ do beneficiário
  (sem CPF/CNPJ, o nome): igual → revisão; diferente → lançamento novo. Pagamentos do DBK que não
  vieram no JSON aparecem no relatório, pela ordem na ficha.
- A linha nova entra depois do último pagamento do DBK, sem reordenar pelo código. **A confirmar no
  roteiro manual** que o programa reordena na restauração.
- Fora do escopo: doações (40 a 47, 80, 81), empregado doméstico (código 50, fora da tabela de 2026) e
  contribuição do ente patrocinador (a tela de 2026 não mostra).

## Alternativas consideradas

- Somar ou substituir o valor de um pagamento igual já no DBK: não dá para saber se é o mesmo recibo
  lançado de novo ou outro pagamento ao mesmo beneficiário; a revisão é mais segura.
- Indicar o dependente pelo nome, como a tela: o CPF é único e já vem nos documentos do cliente.
- Esperar a ficha de dependentes: os pagamentos de saúde e instrução de dependentes já declarados no ano
  anterior (que vêm na importação) ficariam de fora sem necessidade.

## Consequências

- `FICHAS = (rendimentos_pj, pagamentos, bens)`.
- A ficha de dependentes (registro 25), quando existir, precisa rodar antes desta, para que um
  dependente novo possa receber pagamentos na mesma execução.
- Falta confirmar no programa a restauração (ordem das linhas, totais e pendências).
