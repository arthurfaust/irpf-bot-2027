# 0014. Bloco `veiculo` libera veículo, aeronave e embarcação

- **Status:** Aceito (com 0010 e 0012, substitui o 0008)
- **Data:** 16/11/2026

## Contexto

Veículo (02/01) e embarcação (02/03) no Brasil eram recusados por falta do registro no JSON (ADR 0008).
O que se sabe do programa IRPF 2026:

- Um único campo da tela (`Bem.registroBem`) vira `NR_RENAVAN` (veículo, no Brasil ou no exterior),
  `NR_REG_AERONAVE` ou `NR_REG_EMBARCACAO`, conforme o código.
- `Bem$8`: Renavam do veículo no Brasil em branco é **erro**. `ValidadorRenavam`: Renavam inválido
  também é **erro** (9 ou 11 dígitos, só números, dígito verificador conferido).
- `Bem$9`: registro da aeronave ou da embarcação no Brasil em branco é **aviso**.
- O observador `Bem$11` completa com zeros à esquerda até 11 caracteres o registro do veículo com
  menos de 11, no Brasil **e no exterior**.
- Tamanhos da tela (`Bem.tamanhoCampoRegistro`): Renavam 11; registro estrangeiro, aeronave e
  embarcação 30.
- Um DBK gravado pelo programa em 16/11/2026 com 5 bens (`tests/dados/veiculo_programa.DBK`)
  confirmou: `987654322` gravado como `00987654322`, `ABC1234-FL` como `0ABC1234-FL`, `PT-ABC` como
  digitado. O bot gera linhas idênticas byte a byte.

## Decisão

- Bloco `veiculo` no JSON: `renavam` (02/01; no exterior, o registro do veículo no país),
  `registro_aeronave` (02/02) e `registro_embarcacao` (02/03).
- No Brasil, os três são obrigatórios (o da aeronave é só aviso no programa; o bot exige, como nas
  contas). No exterior, o registro do veículo é opcional.
- O Renavam no Brasil é conferido com o algoritmo do programa; a mensagem não repete o número.
- O registro do veículo com menos de 11 caracteres ganha zeros à esquerda, como o programa grava.

## Alternativas consideradas

- Um só campo `registro` no bloco: a origem no JSON ficaria ambígua nas mensagens de erro e a
  validação dependeria do código; três nomes explícitos seguem o padrão dos outros blocos.
- Não conferir o DV do Renavam: o programa recusaria a entrega (erro), e o problema só apareceria lá.

## Consequências

- Nenhum tipo de bem exige mais campo sem caminho no JSON
  (`test_todo_campo_obrigatorio_pode_ser_informado_no_json`); o ADR 0008 está todo substituído.
- A busca por registro (passo seguinte) deve comparar o registro já completado com zeros.
