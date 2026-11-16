# 0013. Chave da busca de ações e de ativos negociados em bolsa

- **Status:** Aceito (complementa 0006, 0007 e 0012)
- **Data:** 16/11/2026

## Contexto

Com o bloco `bolsa` (ADR 0012), ações (03/01) e ativos negociados em bolsa (04/04: BDRs, opções)
passam a ter o código de negociação. No DBK gravado pelo programa em 16/11/2026
(`tests/dados/bolsa_programa.DBK`):

- A PN e a ON da mesma empresa (PETR4 e PETR3) têm o mesmo CNPJ; só o código as separa.
- A ação de empresa fechada tem `IN_BOLSA` 0 e o código em branco.
- O 04/04 não tem CNPJ (a tela não mostra o campo).
- Dois FII com o mesmo CNPJ e códigos diferentes são possíveis (ex.: direitos de subscrição).

Numa declaração anterior ao bloco `bolsa`, ou feita sem cuidado, a mesma ação pode estar sem o código
ou como não negociada.

## Decisão

- Ação no Brasil: grupo + código + CNPJ + código de negociação (vazio se não é negociada).
- 04/04 no Brasil e negociado: grupo + código + código de negociação. Não negociado: sem busca.
- Ação no exterior: sem busca (não há CNPJ).
- Chave incompleta (ADR 0007): ação sem CNPJ, ou negociada sem código, no DBK.
- Família: ação do JSON não encontrada, com outra ação do **mesmo CNPJ** no DBK de entrada, vai para
  revisão (pode ser a mesma ação declarada antes sem o código ou com outro código).
- Fundos continuam com grupo + CNPJ (ADR 0006).

## Alternativas consideradas

- Só CNPJ para ações: a ON atualizaria a PN.
- Lançar como nova a ação com código que não está no DBK, mesmo com outra do mesmo CNPJ: duplicaria a
  ação declarada no ano anterior sem o código.
- Código de negociação também na chave dos fundos: um FII declarado antes com `IN_BOLSA` 0 (o padrão
  antigo do bot) deixaria de ser encontrado; fica para quando houver caso real.

## Consequências

- Compra de outra classe de ação de uma empresa que já está no DBK (ex.: tinha ON e comprou PN) cai em
  revisão, não em lançamento novo.
- FII com dois códigos no mesmo CNPJ continua indo para revisão (2 encontrados); o teste
  `test_fii_com_dois_codigos_no_mesmo_cnpj_vai_para_revisao` documenta a limitação.
