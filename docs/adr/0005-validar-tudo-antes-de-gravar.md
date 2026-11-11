# 0005. Validar tudo antes de gravar; CPF do JSON conferido

- **Status:** Aceito
- **Data:** até 11/11/2026 (registrado em 11/11/2026)

## Contexto

Um DBK gravado pela metade, ou com dados de outro cliente, pode passar despercebido na restauração,
porque o programa confere pouco (ver 0002). Os logs ficam no computador e não podem expor dados do
cliente.

## Decisão

- O `main.py` valida o JSON inteiro (todas as fichas, todos os itens) antes de alterar o DBK. Com
  qualquer erro, nada é gravado e todos os erros são listados de uma vez.
- O `"cpf"` é obrigatório no JSON e precisa ser o CPF do declarante do DBK (adicionado em 11/11/2026).
- Mensagens de erro e logs citam o campo e o formato esperado, nunca o conteúdo (CPF, discriminação,
  valores). Bens aparecem pelo número no JSON e pela chave e pelo grupo/código no DBK.

## Alternativas consideradas

- Gravar os itens válidos e pular os inválidos: deixa uma declaração parcial que parece completa.

## Consequências

- Uma vírgula errada num bem impede a execução inteira; o operador corrige o JSON e roda de novo.
