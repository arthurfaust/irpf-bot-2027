# 0024. Ficha Dependentes

- **Status:** Aceito
- **Data:** 18/11/2026

## Contexto

Quarta ficha do bot (registro 25, 224 posições). Os pagamentos de dependentes (ADR 0021) dependem
dela: hoje um pagamento de dependente que não está no DBK vai para revisão.

Do programa IRPF 2026 (`dependencias.xml`, `racaCor.xml` e classe `Dependente`, lida com `javap`;
detalhes em `leiautes/irpf2026/tabela_dependentes.py`): 10 tipos de dependente; tipo, nome, CPF e data
de nascimento obrigatórios (erro); CPF com dígito, diferente do titular, sem repetir entre dependentes
e diferente dos alimentandos; limites de idade nos tipos 21, 24, 41 (até 21 anos) e 22, 25 (até 24);
e-mail, DDD e celular opcionais com formato conferido; raça/cor opcional.

Um DBK gravado pelo programa em 18/11/2026 com 4 dependentes digitados fora da ordem do tipo
(`tests/dados/dependentes_programa.DBK`) mostrou que o programa **mantém a ordem de digitação** e
numera a chave em sequência; "mora com o titular" é gravado como 1 ou 0 e raça/cor como 0 sem
resposta. A importação da declaração anterior traz o dependente com chave, nome, nascimento e CPF,
mas **sem o tipo** (pendência "Tipo de dependente" no programa).

## Decisão

- Lista `dependentes` no JSON: `tipo`, `nome`, `cpf`, `data_nascimento` (obrigatórios) e
  `mora_com_titular`, `email`, `ddd`, `celular`, `raca_cor` (opcionais).
- Busca pelo CPF nas linhas do DBK de entrada:
  - nenhum → dependente novo, depois do último, com a maior chave do DBK + 1;
  - 1 → campo em branco no DBK recebe o do JSON (é o caso do tipo na importação); campo preenchido e
    diferente fica como está e gera aviso com o nome do campo, como nos bens (ADR 0016);
  - 2 ou mais, ou CPF de um alimentando do DBK → revisão.
- `FICHAS = (rendimentos_pj, dependentes, pagamentos, bens)`: dependentes antes de pagamentos, para um
  dependente novo receber pagamentos na mesma execução.
- O aviso do programa para pais e avós mais novos que o titular não é reproduzido (o bot não lê a data
  de nascimento do titular).

## Alternativas consideradas

- Atualizar todos os campos do dependente encontrado com os do JSON: o cadastro do ano anterior pode
  ter sido corrigido no programa; o critério dos bens mantém o que está preenchido.
- Ordenar os dependentes pelo tipo: o programa não ordena.

## Consequências

- Os dependentes do DBK que não vieram no JSON aparecem no relatório (eles continuam reduzindo o
  imposto; o cliente pode ter deixado de ser dependente).
- Alimentandos (registro 35) continuam fora do escopo: a importação também os traz incompletos.
- Falta o roteiro manual, com restauração no programa.
