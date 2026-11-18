- Diferente dos outros roteiros, o teste1 parte de `base/77039677008-IRPF-A-2026-2025-ORIGI.DBK`, e não
  do DBK vazio: os pagamentos de dependente e alimentando precisam deles no DBK. A base é o
  `tests/dados/pagamentos_programa.DBK` (dependente JOAO TESTE, alimentanda MARIA TESTE, as fontes de
  rendimento do roteiro `rendpj`) sem as linhas de pagamento, gerada pelo bot.
- O teste2 usa a saída do teste1, como nos outros roteiros.
- teste1: 8 pagamentos lançados, fora da ordem do código (o 99 vem primeiro); o 9º vai para revisão
  (dependente que não está no DBK).
- teste2: médico do titular, exterior com o mesmo nome e pensão repetidos vão para revisão; o mesmo
  médico para o dependente e um dentista são lançados (o dentista com parcela não dedutível igual ao
  valor pago).
