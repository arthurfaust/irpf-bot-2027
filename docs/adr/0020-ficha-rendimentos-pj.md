# 0020. Ficha Rendimentos Tributáveis Recebidos de PJ pelo Titular

- **Status:** Aceito
- **Data:** 17/11/2026

## Contexto

Segunda ficha do bot (registro 21). Cada fonte pagadora é uma linha com CPF/CNPJ, nome, rendimentos,
contribuição previdenciária oficial, 13º salário, imposto retido, IRRF sobre o 13º e a data de saída
(só na declaração de saída definitiva). Os rendimentos de PJ de dependentes ficam no registro 32.

Do programa IRPF 2026 (classes `RendPJTitular` e `ColecaoRendPJTitular`, lidas com `javap`):

- CPF/CNPJ com dígito inválido, ou igual ao CPF do declarante: erro; em branco: erro se houver imposto
  retido. Nome em branco: erro. Valores só positivos.
- Pendência "Faltam valores" (erro) quando rendimentos, contribuição, 13º e imposto estão em branco.
- `getRendimentoVazioPorNIFontePagadora`: o programa trabalha com fontes sem valores identificadas pelo
  CPF/CNPJ (as que vêm da importação da declaração anterior ou da pré-preenchida).

Um DBK gravado pelo programa em 17/11/2026 com 3 fontes (`tests/dados/rendpj_programa.DBK`) mostrou o
CPF da fonte alinhado à esquerda com espaços e, além das linhas 21, uma linha 24 (13º salário em
rendimentos exclusivos, código 1), totais nos registros 19 e 20, a maior fonte pagadora no registro 16
e as fontes no cabeçalho, tudo calculado pelo programa.

## Decisão

- Lista `rendimentos_pj` no JSON, um objeto por fonte: `cnpj_cpf`, `nome`, `rendimentos`,
  `contribuicao_previdenciaria`, `imposto_retido`, `decimo_terceiro`, `irrf_decimo_terceiro`. Todos
  obrigatórios (`"0.00"` quando não houver), como os valores dos bens.
- O bot confere o dígito verificador do CPF/CNPJ (módulo 11, `comum/documentos.py`) e recusa o CPF do
  declarante. Para isso `validar` das fichas passa a receber o CPF do declarante.
- O bot grava só a linha 21; as linhas 24, 16, 19, 20 e o cabeçalho ficam para o programa recalcular
  (ADR 0002). **A confirmar no roteiro manual.**
- Busca pelo CPF/CNPJ, só nas linhas do DBK de entrada (ADR 0009):
  - fonte sem valores no DBK → recebe os valores do JSON (e o nome, se estiver em branco);
  - fonte com valores → revisão (pode ser lançamento repetido);
  - 2 ou mais no DBK, ou 2 fontes do JSON para uma só sem valores → revisão;
  - nenhuma → lançamento novo (duas do JSON com o mesmo CPF/CNPJ são lançadas, com aviso).
- Relatório: fontes do DBK que continuam sem valores (o programa acusa erro) e fontes com valores que
  não vieram no JSON, pela ordem na ficha, sem CPF/CNPJ nem nome.
- Data de saída e rendimentos de dependentes: fora do escopo por enquanto.

## Alternativas consideradas

- Atualizar a fonte que já tem valores: rendimentos são do ano; uma fonte com valores no DBK de
  entrada já foi preenchida neste ano (por alguém ou por uma execução anterior do bot).
- Valores opcionais no JSON: a IA poderia omitir o imposto retido sem que ninguém percebesse.

## Consequências

- A ficha `rendimentos_pj` vem antes de `bens` em `FICHAS`; as duas são validadas antes de qualquer
  gravação.
- Falta confirmar no programa que a linha 24 do 13º e os totais são recriados na restauração.
