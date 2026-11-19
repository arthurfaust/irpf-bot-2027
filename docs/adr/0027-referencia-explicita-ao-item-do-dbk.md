# 0027. Referência explícita ao item do DBK (campo "dbk")

- **Status:** Aceito
- **Data:** 19/11/2026
- **Substitui em parte:** 0006, 0016, 0018, 0019, 0020, 0021, 0023, 0024, 0025 (só quando o item traz
  a referência; sem ela, a busca de cada ADR continua valendo)

## Contexto

O ADR 0026 definiu o fluxo: o DBK é exportado para JSON com a referência de cada item, a IA compara
com os documentos do cliente e devolve o JSON de alterações dizendo qual item do DBK cada um atualiza.
Falta o bot aceitar e conferir essa referência.

## Decisão

- Campo opcional `"dbk"` em cada item do JSON, no formato da exportação:
  `{"chave": N}` em bens, dependentes e alimentandos (a chave do item no DBK) e `{"item": N}` em
  rendimentos de PJ e pagamentos (a ordem do item na ficha do DBK de entrada). N inteiro a partir de 1;
  outro formato é erro de validação.
- **A referência substitui a busca, e só ela.** O item indicado é tratado como se a busca o tivesse
  encontrado; o que acontece depois segue a regra de cada ficha (bem: atualizado, ADR 0016; fonte ou
  pagamento com valores: revisão; sem valores: preenchido; dependente e alimentando: campos em branco
  preenchidos).
- Conferência, antes de aceitar (senão o item vai para revisão, com o motivo no log):
  - o item existe no DBK de entrada;
  - é do mesmo tipo: bens, mesmo grupo, código e país; pagamentos, mesmo código, tipo e
    dependente/alimentando;
  - identificador forte, quando os dois lados têm: o mesmo (bens: a chave de busca de busca.py —
    Renavam, IPTU, conta, CNPJ...; dependente e alimentando: CPF; fonte: CPF/CNPJ; pagamento: CPF/CNPJ
    do beneficiário). O nome do beneficiário não é conferido: é justamente o caso em que a IA casa
    nomes diferentes (ex.: pagamento no exterior);
  - dois itens do JSON não indicam o mesmo item do DBK;
  - um item sem referência cuja busca acha um item do DBK indicado por outro também vai para revisão
    (os dois tentariam atualizar a mesma linha).
- O relatório de cada ficha lista os itens "achados pela referência 'dbk', não pela busca".

## Alternativas consideradas

- A referência também liberar a atualização de item com valores (fonte, pagamento): uma fonte com
  valores no DBK deste ano já foi preenchida por alguém; a revisão continua mais segura.
- Referência pela posição da linha no arquivo: muda a cada inserção; a chave (bens, dependentes,
  alimentandos) e a ordem na ficha de entrada (fontes, pagamentos) são as numerações que o contador vê.
- Aceitar a referência sem conferência: um erro da IA atualizaria o item errado.

## Consequências

- O JSON exportado pode voltar ao bot: devolver o JSON de um DBK ao mesmo DBK não cria nem duplica
  nada (teste em tests/test_referencia.py).
- A IA resolve os casos que a busca mandava para revisão: bem sem identificador, imóvel sem IPTU,
  pagamento no exterior com nome diferente, e o que o contador indicar.
- A referência de fontes e pagamentos é a ordem no DBK de **entrada**: o JSON precisa ser gerado a
  partir do mesmo DBK que o bot vai receber.
