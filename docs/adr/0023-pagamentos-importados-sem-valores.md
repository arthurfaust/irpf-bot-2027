# 0023. Pagamentos importados sem valores recebem os valores do JSON

- **Status:** Aceito
- **Data:** 18/11/2026
- **Substitui em parte:** 0021 (o que acontece quando o pagamento já está no DBK)

## Contexto

O ADR 0021 mandava para revisão todo pagamento do JSON igual a um já existente no DBK. Em 18/11/2026
o Arthur montou no IRPF 2025 uma declaração com 7 pagamentos e a importou no IRPF 2026
(`tests/dados/pagamentos_importados.DBK`). A importação traz cada pagamento com código, tipo, chave do
dependente/alimentando, CPF/CNPJ, nome, descrição e país, mas com o **valor pago e a parcela não
dedutível zerados**; o programa acusa "Valor Pago não foi informado" (erro) em cada um. É o mesmo
esquema das fontes pagadoras (ADR 0020).

## Decisão

- Na busca (mesma chave do ADR 0021, só nas linhas do DBK de entrada):
  - 1 pagamento sem valores no DBK → recebe o valor pago e a parcela não dedutível do JSON; a
    descrição do JSON só entra se a do DBK estiver em branco (se for diferente, fica a do DBK e o
    relatório pede para conferir, como no ADR 0016);
  - 1 pagamento com valores → revisão (como antes);
  - 2 ou mais no DBK, ou 2 do JSON para um só sem valores → revisão;
  - nenhum → lançamento novo, na posição do código (ADR 0022).
- O relatório lista os pagamentos do DBK que continuam sem valores (o programa acusa erro) e os com
  valores que não vieram no JSON, pela numeração da ficha **depois da gravação**: com os novos
  entrando na posição do código, a ordem da entrada não é a da tela.

## Alternativas consideradas

- Manter a revisão para tudo que já existe: com a importação, quase todo pagamento recorrente (plano
  de saúde, escola, pensão) iria para revisão.
- Trocar a descrição do DBK pela do JSON: a do DBK foi escrita pelo cliente ou pelo contador no ano
  anterior; o mesmo critério dos bens (ADR 0016) mantém o que está preenchido.

## Consequências

- A busca precisa acompanhar a posição das linhas da entrada depois de cada inserção (os novos entram
  no meio da ficha).
- Confirmar no programa: restaurar o DBK preenchido e ver os valores e as pendências.
