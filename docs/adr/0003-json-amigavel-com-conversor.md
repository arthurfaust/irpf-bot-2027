# 0003. JSON amigável + conversor, em vez do formato do DBK

- **Status:** Aceito
- **Data:** até 10/11/2026 (registrado em 11/11/2026)

## Contexto

O JSON do cliente será gerado por IA a partir de documentos (informes, extratos). A IA erra menos
quando escreve o que está no documento do que quando precisa conhecer os códigos internos do DBK.

## Decisão

O JSON usa nomes e valores legíveis (`"m2"`, `true`, `"situacao_atual"`, blocos `imovel`, `cripto`,
`pertence_a`) e `fichas/bens/entrada.py` converte para os campos e códigos do registro 27. Detalhes:

- Nomes sem ano: `situacao_anterior`/`situacao_atual` (`VALOR_ANTERIOR`/`VALOR_ATUAL` no código).
- `situacao_anterior` e `situacao_atual` são obrigatórias (use `"0.00"`), para a IA não omitir
  um valor por engano.
- Valores aceitos como `"1234.56"` ou número do JSON, sem arredondamento escondido: casa decimal a
  mais, vírgula ou símbolo de moeda é erro.
- `cnpj_cpf` no primeiro nível do bem (ações, fundos, contas, devedor dos créditos); a cripto usa
  `cripto.cnpj_custodiante`. Informar os dois é erro.

## Alternativas consideradas

- JSON com os campos do DBK (`NM_UNID: 0`): acopla a IA ao leiaute de um ano e esconde erros.

## Consequências

- Os códigos do DBK ficam só no código Python, que tem a origem documentada.
- Um JSON Schema gerado das regras poderá ser dado à IA (saída estruturada).
