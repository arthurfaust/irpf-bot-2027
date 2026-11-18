- teste1 parte do DBK vazio (`tests/manual/`) e o teste2 da saída do teste1, como nos outros roteiros.
- teste1: um dependente (cônjuge) e 4 alimentandos: MARIA (decisão judicial), PEDRO (escritura
  pública), ANA (exterior, os dois processos) e LUCAS, alimentando do cônjuge (dependente lançado na
  mesma execução). Pagamentos: pensão da MARIA e escola do PEDRO. O pagamento vazio (código 02) do DBK
  vazio aparece como "continua sem valores".
  No programa: ANA e LUCAS devem continuar com o aviso "Alimentando não relacionado a despesa
  dedutível"; MARIA e PEDRO não.
- teste2: MARIA com outra vara (fica a do DBK, CONFERIR), BRUNO novo (chave 5) e um alimentando de
  alguém que não é titular nem dependente (revisão, não gravado).
- teste3 (separado): parte de `importada/` (cópia de `tests/dados/pagamentos_importados.DBK`, importada
  do IRPF 2025). A MARIA importada recebe a data de nascimento e a decisão judicial; a pensão e a
  escola dela, importadas sem valor, são preenchidas.
- Em todos: a confirmação "Estou ciente..." não é gravada no DBK; marque no programa antes de
  conferir as pendências (o relatório lembra).
