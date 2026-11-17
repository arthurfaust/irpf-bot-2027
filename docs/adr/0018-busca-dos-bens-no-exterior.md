# 0018. Busca dos bens no exterior

- **Status:** Aceito (complementa 0006, 0007 e 0013; substitui em parte o 0015: veículo do exterior sem registro)
- **Data:** 17/11/2026

## Contexto

No exterior a tela não mostra CNPJ, banco, agência nem conta. Pelas regras da tela, só alguns bens do
exterior têm campo que os identifique: ações e fundo no exterior (07/99) negociados em bolsa (código de
negociação), criptoativos (o ativo), imóveis (endereço) e veículos, aeronaves e embarcações (registro,
opcional no exterior). Conta corrente, ação ou fundo não negociado, títulos, créditos, VGBL, joias e
outros só têm grupo, código, país e discriminação.

Sem busca, esses bens entravam como lançamento novo todo ano, duplicando o do ano anterior.

Decisão tomada pelo Arthur em 17/11/2026.

## Decisão

- Chaves no exterior (país sempre na chave):
  - ações (03/01) e fundo (07/99) negociados: grupo + código + país + código de negociação;
  - cripto 08/01-03 custodiado: grupo + código + ativo + "EXTERIOR" + país (autocustodiante continua
    com a chave do ADR 0007);
  - imóvel: grupo + código + país + logradouro + número, em maiúsculas, só letras e números.
- Bens do exterior **sem identificador** (todos os outros, inclusive ação/fundo não negociado e veículo
  sem registro): se o DBK de entrada já tem bem do mesmo grupo, código e país, o bem do JSON vai para
  revisão; se não tem, é lançado como novo. No relatório, os do DBK aparecem como "bem do exterior sem
  campo identificador: confira e atualize no programa".
- Ação do exterior negociada não encontrada, com ação do mesmo país sem código no DBK: revisão (chave
  incompleta, ADR 0007).

## Alternativas consideradas

- Lançar como novo, com aviso, o bem sem identificador: o programa ficaria com o bem repetido até
  alguém excluir.
- Comparar pela discriminação: texto livre, reescrito pela IA a cada ano.
- Deixar o imóvel sem chave: o endereço é texto livre, mas logradouro e número variam pouco depois da
  normalização.

## Consequências

- Cliente com duas contas no mesmo país (ou dois fundos não negociados) sempre terá revisão manual
  desses bens; é o custo de não duplicar.
- Os bens sem busca no Brasil (imóveis, joias, quotas etc.) continuam entrando como novos; a mesma regra
  pode ser estendida a eles depois.
