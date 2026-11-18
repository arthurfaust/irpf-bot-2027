- teste1 parte do DBK vazio (`tests/manual/`) e o teste2 da saída do teste1, como nos outros roteiros.
- teste1: 4 dependentes novos, na ordem 31, 21, 11, 22 (chaves 1 a 4), e 2 pagamentos para dependentes
  lançados na mesma execução (o plano do filho e a faculdade do universitário). O pagamento vazio
  (código 02) que o DBK vazio já tinha aparece no relatório como "continua sem valores".
- teste2: filho com nome diferente (fica o do DBK, CONFERIR), cônjuge igual (nada muda) e um neto
  novo (tipo 24, chave 5). Pai e universitário aparecem como "não vieram no JSON".
- teste3 (separado): parte de `importada/`, a declaração importada do IRPF 2025 (cópia de
  `tests/dados/pagamentos_importados.DBK`). O JOAO importado sem o tipo recebe o tipo 21 e a raça/cor;
  "mora com o titular" fica 0 (não), como veio do DBK, com CONFERIR. A mãe é nova (chave 2). O plano
  do JOAO é preenchido; os outros 6 pagamentos importados continuam sem valores.
