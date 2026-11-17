# 0015. Chave da busca de veículo, aeronave e embarcação

- **Status:** Aceito (complementa 0006 e 0007); substituído em parte por 0018 (veículo do exterior sem registro)
- **Data:** 17/11/2026

## Contexto

Com o bloco `veiculo` (ADR 0014), veículo (02/01), aeronave (02/02) e embarcação (02/03) têm um
registro que identifica o bem. No DBK gravado pelo programa em 16/11/2026
(`tests/dados/veiculo_programa.DBK`):

- O registro do veículo com menos de 11 caracteres é gravado com zeros à esquerda, também no
  exterior (`987654322` → `00987654322`; `ABC1234-FL` → `0ABC1234-FL`).
- Os registros de aeronave e embarcação ficam como digitados, com hífen (`PT-ABC`).
- No Brasil o registro é obrigatório; no exterior, opcional.

## Decisão

- Chave: grupo + código + país + registro. O registro é comparado em maiúsculas, só com letras e
  números e sem zeros à esquerda ("PT-ABC" = "ptabc"; "00987654322" = "987654322").
- O país entra na chave e no tipo: um registro em branco no exterior (permitido) só marca como chave
  incompleta os bens do mesmo código naquele país, sem bloquear os do Brasil.
- Registro em branco no DBK = chave incompleta (ADR 0007): o bem do JSON do mesmo grupo, código e país
  sem correspondente vai para revisão.
- Bem do JSON no exterior sem registro: sem busca, lançado como novo.

## Alternativas consideradas

- Comparar o registro exatamente como gravado: "PT-ABC" e "PTABC" seriam bens diferentes, e o Renavam
  de 9 dígitos digitado com 11 não seria encontrado.
- Deixar o país fora da chave: um veículo do exterior sem registro mandaria para revisão todo veículo
  novo do Brasil.

## Consequências

- Um veículo que mudou de país entra como novo, e o do DBK aparece no relatório como não atualizado.
- Registros diferentes só na pontuação são tratados como o mesmo bem.
