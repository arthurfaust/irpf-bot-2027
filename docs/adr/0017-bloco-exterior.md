# 0017. Bloco `exterior`: valores do ano das aplicações e dividendos no exterior

- **Status:** Aceito (complementa 0002 e 0016)
- **Data:** 17/11/2026

## Contexto

Bens no exterior (Lei 14.754/2023) têm quatro valores do ano no registro 27, que a tela mostra conforme
o grupo/código (regras `APLICACAO_FINANCEIRA_EXTERIOR` e `LUCROS_DIVIDENDOS_EXTERIOR`):

- lucro ou prejuízo da aplicação financeira (`Bem.lucroPrejuizo`, `Valor`: aceita negativo);
- imposto pago no exterior sobre a aplicação, valor recebido de lucros e dividendos e imposto pago
  sobre eles (`ValorPositivo`).

Não há validador de obrigatoriedade. Um DBK gravado pelo programa em 17/11/2026 com 4 bens
(`tests/dados/exterior_programa.DBK`) mostrou:

- o prejuízo gravado como `-000000025000` (-250,00), o formato que `Campo.formatar` já produz;
- linhas 37 (demonstrativo por bem: tipo 1 aplicação / 2 dividendos, 15% de imposto devido, base,
  saldo) e uma linha 24 (rendimento de tributação exclusiva, código 13), além de totais no registro 20,
  `IN_CRIT_OBRIGAT` no cabeçalho e um indicador no registro 16. Tudo isso o programa calcula a partir
  das linhas 27.

## Decisão

- Bloco `exterior` no JSON: `lucro_prejuizo`, `imposto_pago`, `dividendos_recebidos`,
  `imposto_dividendos`. Todos opcionais; só `lucro_prejuizo` aceita negativo.
- O bot grava só a linha 27. As linhas 24 e 37, os totais e os indicadores ficam para o programa
  recalcular na restauração (como no ADR 0002). **A confirmar no roteiro manual** (ida e volta).
- Bem encontrado no DBK: os quatro valores, quando vêm no JSON, substituem os do DBK (são do ano, como a
  situação atual). Sem o bloco no JSON, os do DBK ficam.

## Alternativas consideradas

- Gravar também as linhas 24 e 37: repetiria cálculos do programa (15%, compensação de prejuízo,
  saldo) que ele já refaz; um erro nosso ficaria no arquivo.
- Tratar os valores do ano como os demais campos do ADR 0016 (manter o do DBK e avisar): o valor do
  ano anterior ficaria no lugar do deste ano.

## Consequências

- Se a restauração não recriar as linhas 24 e 37, o imposto da Lei 14.754 fica faltando: o roteiro
  manual precisa conferir a ficha "Rendimentos sujeitos à tributação exclusiva" e o arquivo regravado.
- A maior parte dos bens do exterior ainda não tem busca (conta, ações, fundo, cripto custodiada):
  a cada ano eles entram como lançamento novo. Falta definir uma chave para eles.
