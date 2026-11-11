# 0007. Chave da cripto e salvaguarda de chave incompleta

- **Status:** Aceito
- **Data:** 11/11/2026

## Contexto

Para criptoativos, o programa pergunta "É autocustodiante?" (08/01, 02, 03 e 10) e, se a resposta for
não e o bem estiver no Brasil, pede o CNPJ do custodiante. Altcoins (08/02) e stablecoins (08/03) têm
a sigla do ativo. Fora do Brasil não há campo de CNPJ. NFTs (08/10) e outros (08/99) não têm campo que
identifique o ativo. Esses campos são recentes: declarações antigas podem ter a cripto sem eles.

## Decisão

Chave da cripto (só 08/01, 08/02 e 08/03):

| Situação | Chave |
|---|---|
| Autocustodiante | grupo + código + sigla do ativo + "AUTO" |
| Custodiado no Brasil | grupo + código + sigla do ativo + CNPJ do custodiante |
| Custodiado no exterior, NFT, outros | sem busca: lançamento novo |

A sigla é comparada sem espaços e em maiúsculas; no bitcoin ela é vazia.

**Chave incompleta** (vale para todos os tipos com busca): um bem do DBK de tipo com busca, mas com
algum campo da chave em branco (ex.: cripto no Brasil, não autocustodiante, sem CNPJ), não é
encontrado por nenhum bem do JSON. Se um bem do JSON não encontra nada e o DBK tem um bem do mesmo
tipo (grupo + código; nos fundos, o grupo) com a chave incompleta, ele vai para revisão em vez de ser
lançado. No relatório, esse bem do DBK aparece com "dados da chave em branco no DBK".

## Alternativas consideradas

- Autocustodiante sem busca: evitaria atualizar a carteira errada quando o cliente tem duas carteiras
  próprias do mesmo ativo, mas lançaria em duplicidade o caso comum (uma carteira por ativo).
  Duas carteiras do mesmo ativo já no DBK caem em revisão (2+).
- Chave incompleta comparada também pela sigla: uma altcoin antiga sem sigla escaparia da salvaguarda.

## Consequências

- Se o cliente abriu uma segunda carteira própria do mesmo ativo e o DBK tem só uma, o bot atualiza a
  existente; o relatório não detecta esse caso.
- Uma cripto antiga sem custodiante bloqueia (manda para revisão) os bens do JSON do mesmo código até
  ser completada no programa.
