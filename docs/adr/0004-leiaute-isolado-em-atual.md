# 0004. Leiaute do ano isolado em `leiautes/atual.py`

- **Status:** Aceito
- **Data:** até 10/11/2026 (registrado em 11/11/2026)

## Contexto

O leiaute do DBK, as tabelas (grupos/códigos, países) e as regras da tela mudam a cada exercício. O
projeto começou no IRPF 2026 e o alvo é o IRPF 2027.

## Decisão

Tudo o que depende do ano fica em `leiautes/irpfAAAA/`. O resto do código importa só de
`leiautes/atual.py`, que reexporta o leiaute em uso. Trocar de ano = criar `leiautes/irpf2027/` e
mudar os imports de `atual.py`. O `dbk/` (Campo, Registro, ArquivoDBK) é genérico e não muda.
O `main.py` confere se o exercício do DBK é o do leiaute em uso e recusa o arquivo se não for.

## Alternativas consideradas

- Variável `LEIAUTE` no `.env` com import dinâmico: com um leiaute só, seria complexidade sem uso.

## Consequências

- Um ano de cada vez por execução; para dois anos ao mesmo tempo seria preciso revisitar esta decisão.
- Cada módulo do leiaute documenta a origem (arquivo do programa, classe lida com `javap` ou
  "confirmado em DBK").
