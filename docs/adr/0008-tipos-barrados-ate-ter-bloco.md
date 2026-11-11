# 0008. Tipos de bem barrados até o JSON ter o bloco deles

- **Status:** Aceito
- **Data:** até 10/11/2026 (registrado em 11/11/2026)

## Contexto

O programa exige campos que o JSON ainda não tem: banco, agência e conta para conta corrente e
poupança; Renavam do veículo e registro da embarcação no Brasil.

## Decisão

Conta corrente, poupança, veículo e embarcação no Brasil são recusados na validação até a fase 4 criar
os blocos `conta` e `veiculo`. "Negociado em bolsa?" não é exigido (padrão "Não"), e no imóvel no
exterior só logradouro, área e unidade são exigidos.

## Alternativas consideradas

- Lançar sem os campos: o programa abriria a declaração com pendências, ou recusaria o arquivo.

## Consequências

- Pendente de confirmação: se o programa aceita o padrão "Não" em "Negociado em bolsa?" e o validador
  completo do imóvel no exterior.
