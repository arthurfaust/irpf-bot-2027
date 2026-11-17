# 0019. Busca dos demais bens do Brasil

- **Status:** Aceito (complementa 0006, 0007, 0013 e 0018)
- **Data:** 17/11/2026

## Contexto

Depois dos ADRs 0006 a 0018, ainda entravam como lançamento novo todo ano, duplicando o do ano anterior,
os bens do Brasil sem chave: imóveis, quotas, títulos e aplicações, créditos, outros depósitos,
consórcio, VGBL, JCP, NFT, joias, quadros, dinheiro em espécie e outros.

Pelas regras da tela:

- imóvel no Brasil tem um campo de registro conforme o código (`REGISTRO_IMOVEL`: IPTU nos urbanos,
  CIB no rural 14, CEI/CNO na construção 16, nenhum nas benfeitorias 17), opcional, e a matrícula +
  cartório quando registrado em cartório;
- vários tipos têm CNPJ/CPF (`TEM_CNPJ_CPF`): obrigatório em quotas, títulos, consórcio, VGBL e JCP;
  opcional nos créditos (CPF/CNPJ do devedor);
- os demais não têm nenhum campo que identifique o bem.

Decisão tomada pelo Arthur em 17/11/2026.

## Decisão

- **Imóvel no Brasil:** chave = registro do código (IPTU, CIB ou CEI/CNO); sem ele, matrícula +
  cartório. Comparados em maiúsculas, só letras e números (o registro sem zeros à esquerda).
  Família: imóveis do mesmo código no mesmo município; imóvel do JSON não encontrado, com outro da
  mesma família no DBK, vai para revisão (pode ser o mesmo com outro identificador). Sem registro nem
  matrícula: sem identificador.
- **Bens do Brasil com CNPJ/CPF** ainda sem chave própria: grupo + código + país + CNPJ/CPF. Vários do
  mesmo CNPJ (ex.: dois CDBs no mesmo banco) caem em revisão pela regra da chave repetida (ADR 0006 e
  0009). Sem o CNPJ/CPF: sem identificador.
- **Bens do Brasil sem identificador** (joias, quadros, dinheiro em espécie, NFT autocustodiado, BDR não
  negociado etc.): a regra do ADR 0018 passa a valer também no Brasil. Se o DBK de entrada tem bem do
  mesmo grupo, código e país, o bem do JSON vai para revisão; senão, é lançado como novo.
- Com isso todo bem tem identificação na busca; a mensagem "tipo sem busca automática" deixa de
  aparecer, e o relatório diz "bem sem campo identificador: confira e atualize no programa".

## Alternativas consideradas

- Imóvel só pelo registro: imóvel com matrícula e sem IPTU seria sempre "sem identificador".
- Bens com CNPJ tratados como sem identificador: cliente com um título em cada banco cairia sempre em
  revisão.
- Lançar como novo o bem sem identificador: mantinha a duplicação a cada ano.

## Consequências

- Cliente com dois imóveis do mesmo código na mesma cidade, um deles novo e sem o mesmo identificador
  do outro, terá revisão manual do novo.
- Vários títulos no mesmo banco, joias, dinheiro em espécie etc. passam a exigir revisão manual todo
  ano, em vez de duplicar.
- A saída de referência (`tests/dados/esperado.DBK`) e os roteiros manuais não mudaram.
