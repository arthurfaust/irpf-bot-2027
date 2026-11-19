# Plano do irpf-bot-2027

Situação em 11/11/2026 (último commit: `b22cdf0` + pendências resolvidas). 196 testes passando.

## Visão geral do fluxo

```
Arquivos do cliente (pdf, csv) → censura de dados sensíveis → IA → JSON
                                                                    │
DBK (cópia de segurança do IRPF, com a declaração anterior importada) ┤
                                                                    ▼
          1. Validar TODO o JSON (formato + regras da tela) — erro → nada é gravado
          2. Para cada lançamento: montar a chave → procurar no DBK
               1 encontrado → atualizar | 0 → lançar completo | 2+ → revisão   (fase 3)
          3. Bens do DBK que não vieram no JSON → revisão                       (fase 3)
          4. Gravar o DBK + relatório para conferência humana
```

A IA só estrutura os dados; quem decide o que gravar é o código, de forma determinística.

## Concluído

| Fase | Conteúdo |
|---|---|
| Base | Inserção de bens (registro 27) a partir do JSON; importado com sucesso no IRPF 2026 |
| 0 | Rede de segurança: pytest + comparação byte a byte com `tests/dados/esperado.DBK` |
| 1 | Refatoração: `dbk/`, `comum/`, `leiautes/irpf2026/` + `leiautes/atual.py`, `fichas/bens/`, `FICHAS`, `config.py`, conferência do exercício do DBK |
| 2 | Validação completa: campos básicos obrigatórios e desconhecidos, normalização de texto (Latin-1, tamanho), formato de valores, país e restrições Brasil/exterior, obrigatórios por tipo de bem |

## Próximas fases

### Fase 3 — procurar e atualizar

Andamento (11/11/2026):
- [x] `Registro.ler_tudo(linha)` e `ArquivoDBK.substituir(posicao, linha)`.
- [x] Busca dos **fundos nacionais** (grupo 07 com CNPJ obrigatório, inclusive FII/FIA/ETF) por
  grupo + CNPJ, em `fichas/bens/busca.py`. Escolhidos primeiro porque o CNPJ é obrigatório no
  programa e único por fundo. 1 → só `VALOR_ATUAL` (situação anterior divergente gera aviso; a do DBK
  é mantida); 0 → lançamento completo; 2+ → revisão. Dois bens do JSON com a mesma chave existente
  no DBK → os dois vão para revisão.
- [x] Bens do DBK não atualizados pelo JSON → `Resultado.nao_informados` (nunca zerados nem
  apagados); os de tipo sem busca vêm com o aviso de conferir duplicidade. Relatório no log ao fim
  da execução (`ficha.relatorio`), sem dados do cliente: bens do JSON pelo número, bens do DBK pela
  chave e pelo grupo/código. A busca só casa com linhas do DBK que também são fundos nacionais.
- [x] **Confirmado no programa IRPF 2026 (11/11/2026)** com o roteiro `tests/manual/fundos/`: as duas
  saídas foram restauradas; fundos novos lançados, A e B atualizados só na situação em 31/12/2025
  (situação anterior e discriminação mantidas), C novo, sem duplicidade, totais 18.000,00/30.000,00.
  O programa renumera os itens na tela (a CHAVE do DBK não é o número do item).
- [x] Busca de **cripto** 08/01-03 (autocustodiante ou custodiado no Brasil) e salvaguarda de
  chave incompleta: bem do JSON sem correspondente vai para revisão se o DBK tem bem do mesmo tipo
  com a chave em branco (ADR 0007).
- [x] Teste manual de 13/11/2026 com DBK sem bens (`tests/manual/`): achou o bug do 2º bem do JSON
  encontrar a linha que o 1º acabara de lançar. Corrigido: a busca olha só os bens do DBK de entrada
  (ADR 0009).
- [x] **Confirmado no programa IRPF 2026 (13/11/2026)** com as saídas encadeadas (teste1 → teste2)
  de fundos e cripto. Cripto: BTC autocustodiante e ETH na corretora X atualizados, ETH na corretora
  Z e BTC no exterior lançados como novos, USDT repetido no JSON mantido como estava (revisão), totais
  4.500,00/15.700,00. Fundos: A e B atualizados, C novo, D repetido no JSON lançado duas vezes, totais
  15.000,00/27.000,00.
- [x] Campos do bem encontrado (17/11/2026, ADR 0016): discriminação do JSON em ações, BDRs, fundos e
  cripto (onde a quantidade muda todo ano), a do DBK nos demais (com aviso); campo em branco no DBK
  recebe o do JSON; preenchido e diferente (inclusive grupo/código/país) fica o do DBK, com aviso e o
  bem na linha "CONFERIR" do relatório. Mais adiante, a IA pode montar a discriminação.
- [x] Quadros do exterior (rendimento e imposto do ano) na atualização: sempre os do JSON (ADR 0017).

1. Tipo inicial: fundos nacionais (decidido). Conta corrente/poupança têm a chave mais confiável
   (banco + agência + conta), mas dependem do bloco `conta` (fase 4).
2. Chave de identificação por tipo de bem (proposta):

   | Bem | Chave |
   |---|---|
   | Conta corrente / poupança | banco + agência + conta |
   | Imóvel no Brasil | IPTU, ou matrícula, ou CIB |
   | Veículo | Renavam |
   | Ações, FII, ETF | CNPJ + código de negociação |
   | Fundos, aplicações, títulos | CNPJ |
   | Cripto | código + altcoin/stablecoin + CNPJ do custodiante |
   | Sem campo identificador | não busca automático → revisão |

3. Três resultados: 1 encontrado → atualiza a situação atual (e campos anuais: discriminação,
   quadros do exterior; campo vazio no DBK pode ser preenchido, campo preenchido nunca é sobrescrito
   sem revisão); 0 → lançamento completo; 2+ → não grava, vai para revisão.
   **Nunca altere VALOR_ANTERIOR** de um bem existente (vem da declaração anterior).
4. Bens do DBK ausentes do JSON → lista de revisão (nunca zerar ou apagar automaticamente).
5. Relatório da execução: atualizados, novos, ambíguos, não encontrados.
6. `ArquivoDBK` vai precisar substituir linhas; `Registro` vai precisar de `ler_tudo(linha) -> dict`.

Nem toda ficha tem "procurar": rendimentos são do ano (sempre lançamento novo); bens, dívidas e
dependentes passam de um ano para o outro. A busca deve ser opção de cada ficha.

### Fase 4 — novos blocos de bens

- [x] `conta` (13/11/2026, ADR 0010): banco, agência, conta, DV e conta pagamento; libera poupança e
  conta corrente. As linhas geradas são idênticas às de um DBK gravado pelo programa com 6 contas
  (`tests/dados/contas_programa.DBK`). Na tela de bens não há campo Operação da Caixa.
- [x] Busca de conta (16/11/2026, ADR 0011): grupo + código + banco + agência + conta sem zeros à
  esquerda; conta com DV ou campo em branco no DBK = chave incompleta (revisão).
- [x] Roteiro manual `tests/manual/contas/` (teste1_inserir → teste2_atualizar), como fundos e cripto.
- [x] **Confirmado no programa IRPF 2026 (16/11/2026)**: as duas saídas do roteiro de contas foram
  restauradas. teste1: 4 contas novas, totais 3.900,00/5.000,00. teste2: corrente BB, poupança Caixa
  e poupança Itaú atualizadas (situação anterior mantida), Nubank e corrente Caixa novas, corrente
  Itaú intacta (não informada), totais 3.900,00/8.150,00. Ida e volta: restauradas e gravadas de novo
  pelo programa, as linhas 27 voltaram idênticas byte a byte (inclusive a conta da Caixa com 12
  dígitos e a conta pagamento); só mudaram IR, 20 e T9, que o programa recalcula (ADR 0002). Em
  "Verificar pendências", os bens só têm o aviso de DV inválido (DVs fictícios), que não impede a entrega.

- [x] `bolsa` (16/11/2026, ADR 0012): "Negociados em Bolsa?" obrigatório onde o programa pergunta
  (no programa, em branco é erro) e código de negociação obrigatório quando sim (até 13 caracteres).
  Linhas idênticas às de um DBK gravado pelo programa com 6 bens (`tests/dados/bolsa_programa.DBK`).
- [x] Busca de ações (16/11/2026, ADR 0013): 03/01 por CNPJ + código de negociação (vazio se não
  negociada), 04/04 pelo código; ação não encontrada com outra do mesmo CNPJ no DBK vai para revisão.
- [ ] Fundos com o mesmo CNPJ e códigos diferentes (ex.: direitos de subscrição de FII) continuam em
  revisão pela chave grupo + CNPJ (limitação registrada no ADR 0013).
- [x] Roteiro manual `tests/manual/bolsa/` (teste1_inserir → teste2_atualizar), como os anteriores.
- [x] **Confirmado no programa IRPF 2026 (16/11/2026)**: as duas saídas do roteiro de bolsa foram
  restauradas e gravadas de novo; as linhas 27 voltaram idênticas byte a byte (5 de 5 e 7 de 7); só
  mudaram IR, 20 e T9, que o programa recalcula (ADR 0002).

- [x] `veiculo` (16/11/2026, ADR 0014): Renavam (conferido com o algoritmo do programa), registro de
  aeronave e de embarcação; registro do veículo com menos de 11 caracteres ganha zeros à esquerda,
  também no exterior. Linhas idênticas às de um DBK gravado pelo programa com 5 bens
  (`tests/dados/veiculo_programa.DBK`). Nenhum tipo de bem fica mais barrado (ADR 0008 substituído).
- [x] Busca de veículo, aeronave e embarcação (17/11/2026, ADR 0015): grupo + código + país +
  registro (maiúsculas, só letras e números, sem zeros à esquerda).
- [x] Roteiro manual `tests/manual/veiculo/` (teste1_inserir → teste2_atualizar), como os anteriores.
- [x] **Confirmado no programa IRPF 2026 (17/11/2026)**: as duas saídas do roteiro de veículos foram
  restauradas e gravadas de novo; as linhas 27 voltaram idênticas byte a byte (5 de 5 e 7 de 7, totais
  320.000,00/400.000,00 e 320.000,00/462.000,00); só mudaram IR, 20 e T9 (ADR 0002).

- [x] `exterior` (17/11/2026, ADR 0017): lucro ou prejuízo (aceita negativo), imposto pago, lucros e
  dividendos recebidos e imposto sobre eles. Linhas idênticas às de um DBK gravado pelo programa com
  4 bens (`tests/dados/exterior_programa.DBK`). O bot grava só a 27; as linhas 24 (exclusivo, código
  13) e 37 (demonstrativo) ficam para o programa.
- [x] Roteiro manual `tests/manual/exterior/` (teste1_inserir → teste2_atualizar).
- [x] **Confirmado no programa IRPF 2026 (17/11/2026)**, com ida e volta: a restauração do DBK do bot
  (só linhas 27) recriou a linha 24 (exclusivo, código 13: 1.555,00 no teste1 e 1.835,00 no teste2)
  e as 5 linhas 37, iguais às do DBK digitado na tela; as linhas 27 voltaram idênticas (4 de 4 nos
  dois testes). A decisão do ADR 0017 de não gravar 24 e 37 está confirmada.
- [x] Busca dos bens do exterior (17/11/2026, ADR 0018): ações/fundo negociados pelo código, cripto
  custodiada pelo ativo, imóvel pelo endereço (sempre com o país); os sem identificador vão para
  revisão se o DBK já tem bem do mesmo grupo, código e país.
- [x] Roteiro manual do exterior atualizado para a busca (teste2: atualiza ações e BTC, manda conta e
  fundo não negociado para revisão, lança conta na Alemanha, BTC em corretora e imóvel).
- [x] **Confirmado no programa IRPF 2026 (17/11/2026)**, novo teste2 do exterior com ida e volta: 7 de
  7 linhas 27 idênticas (inclusive o apartamento em Miami, primeiro imóvel no exterior gravado pelo
  bot), linha 24 recriada com 2.130,00 (o valor previsto) e 7 linhas 37; totais 38.000,00/144.500,00.
  "Verificar pendências" sem nenhum item em Bens e Direitos: o imóvel no exterior com logradouro,
  número, área, unidade e data de aquisição basta (fecha a pendência do ADR 0008).
- [x] Demais bens do Brasil (17/11/2026, ADR 0019): imóvel pelo IPTU/CIB/CEI ou matrícula + cartório
  (família: mesmo código e município); bens com CNPJ/CPF por grupo + código + CNPJ; os sem
  identificador vão para revisão se o DBK tem bem do mesmo grupo e código. Todo bem tem busca agora.
- [x] Roteiro manual `tests/manual/brasil/` (imóveis, CDBs, joia, quotas; teste1_inserir → teste2_atualizar).
- [x] **Confirmado no programa IRPF 2026 (17/11/2026)**: roteiro `brasil` restaurado e gravado de novo;
  linhas 27 idênticas byte a byte (6 de 6 e 8 de 8), totais 569.000,00/570.200,00 e
  569.000,00/1.261.200,00.

### Fase 4b — outras fichas (antes da fase 5; reservar janeiro para a fase 5)

Decidido em 17/11/2026: fazer as fichas mais comuns antes da preparação para 2027.

- [x] Rendimentos Tributáveis Recebidos de PJ pelo Titular (registro 21, ADR 0020): validação (CPF/CNPJ
  com dígito, diferente do declarante, nome, valores), busca pelo CPF/CNPJ (fonte sem valores no DBK
  é preenchida; com valores, revisão). Linhas idênticas às de um DBK do programa com 3 fontes.
- [x] A importação da declaração anterior traz as fontes com nome e CNPJ e os valores zerados
  (Arthur, 17/11/2026). Fonte do JSON com os quatro valores principais zerados passa a ser recusada.
- [x] Roteiro manual `tests/manual/rendpj/`: teste1 parte de um DBK que simula a importação (2 fontes
  sem valores) e preenche as duas + lança uma nova; teste2 manda para revisão a que já tem valores.
- [x] Confirmado no programa em 17/11/2026, com ida e volta: as linhas 21 regravadas são idênticas às
  do bot nos dois testes; o programa recria a linha 24 do 13º (código 1, 7.000,00); o "Faltam
  valores" do DBK importado some depois do teste1 e nenhuma pendência da ficha aparece.
- [x] Pagamentos Efetuados (registro 26, ADR 0021): campos e obrigatoriedade por código (tela do
  programa), dependente/alimentando pelo CPF nos registros 25/35 do DBK, pensão com CPF e nome do
  alimentando, busca por código + tipo + dependente + beneficiário (igual → revisão). Linhas idênticas
  às de um DBK do programa com 8 pagamentos.
- [x] Roteiro manual `tests/manual/pagamentos/`: teste1 parte de uma base com dependente e alimentanda
  e lança 8 pagamentos fora da ordem do código (+1 revisão: dependente fora do DBK); teste2 manda 3
  repetidos para revisão e lança 2.
- [x] Confirmado no programa em 18/11/2026, com ida e volta: as linhas 26 regravadas são idênticas às
  do bot nos dois testes, mas o programa as ordena pelo código (no mesmo código, mantém a ordem).
  Linhas 21, 24, 25 e 35 inalteradas. O bot passou a inserir na posição do código (ADR 0022); as
  saídas regeradas têm as linhas 26 na mesma ordem dos regravados. Verificar pendências sem nenhum
  item de Pagamentos Efetuados (parcela não dedutível igual ao valor pago aceita); só as do cadastro
  da alimentanda ("Alimentando do", tipo de processo), que o bot não preenche.
- [x] A importação da declaração anterior traz os pagamentos com todos os campos e o valor pago e a
  parcela não dedutível zerados (confirmado importando do IRPF 2025 em 18/11/2026). A busca passou a
  preencher o pagamento sem valores (ADR 0023); o relatório numera pela ficha já gravada.
- [x] Roteiro `tests/manual/pagamentos/teste3_importada/` confirmado no programa em 18/11/2026, com ida
  e volta: as 8 linhas 26 regravadas são idênticas às do bot, na mesma ordem (6 preenchidas, o 36 novo
  antes do aluguel); só os totais (19 e 20) foram recalculados pelo programa.
- [x] Dependentes (registro 25, ADR 0024): validação (tipos, idade, CPF, contato, raça/cor), busca pelo
  CPF (encontrado: campos em branco preenchidos, como o tipo que a importação não traz; diferente →
  aviso), novo com a próxima chave. Linhas idênticas às de um DBK do programa com 4 dependentes.
  A ficha roda antes de pagamentos.
- [x] Roteiro manual `tests/manual/dependentes/`: teste1 (4 novos + 2 pagamentos deles), teste2 (nome
  diferente mantido, neto novo com chave 5), teste3 a partir da importada (tipo preenchido, mãe nova).
- [x] Confirmado no programa em 18/11/2026, com ida e volta: linhas 25 e 26 regravadas idênticas às do
  bot, exceto o DDD/celular do cônjuge, que o programa descartou porque o titular de teste mora no
  exterior e o cônjuge "mora com o titular" (regra da tela; registrado na ficha). Pendência "Tipo de
  dependente" do importado sumiu. Pendência "Nome tem caracteres inválidos" com hífen no nome: o bot
  passou a recusar nome fora da regra do programa (ValidadorNomeIRPF, `nome_pessoa.py`); os JSONs do
  roteiro foram corrigidos e as saídas regeradas. teste3 restaurado de novo: linhas 25, 26 e 35
  idênticas e nenhuma pendência de Dependentes.
- [x] Alimentandos (registro 35, ADR 0025): validação (nome, CPF, residência, "Alimentando do", decisão
  judicial e/ou escritura pública com as datas), busca pelo CPF como nos dependentes (a importada
  recebe nascimento e tipo de processo e fica igual à digitada no programa). A confirmação "atendem aos
  requisitos" não é gravada no DBK (testado no programa); o relatório lembra de marcá-la.
- [x] Roteiro manual `tests/manual/alimentandos/`: teste1 (4 alimentandos, um deles do cônjuge lançado
  na mesma execução, + pensão e escola), teste2 (vara diferente mantida, novo, revisão por "Alimentando
  do" desconhecido), teste3 a partir da importada (nascimento e processo preenchidos).
- [x] Confirmado no programa em 18/11/2026, com ida e volta: linhas 25, 26 e 35 regravadas idênticas às
  do bot nos três testes. Pendências como esperado: aviso "não relacionado a despesa dedutível" só nos
  alimentandos sem pagamento; data de nascimento e tipo de processo da importada resolvidos; só sobra
  a confirmação dos requisitos (não gravada no DBK).
- [x] Roteiro geral `tests/manual/geral/` (18/11/2026): todas as fichas num cliente; teste2 roda o mesmo
  JSON de novo e confirma que nada é duplicado; teste3 parte da declaração importada. Rodar com
  `bash tests/manual/geral/rodar.sh`. **Atualizar a cada ficha nova.** O roteiro mostrou que a fonte
  em revisão aparecia também como "não veio no JSON"; corrigido (como nos pagamentos).
- [x] Roteiro geral confirmado no programa em 19/11/2026, com ida e volta: registros 21, 25, 26 e 35
  idênticos nos três testes; teste3 idêntico por inteiro. Nos bens, o programa regravou o cartório
  "1º RI" como "1o RI" (e mudou a posição do imóvel, mantendo a chave). A busca e a comparação do bem
  encontrado passaram a tratar "º"/"ª" como "o"/"a"; confirmado rodando o JSON sobre o regravado.
- [x] Dígito verificador da conta (19/11/2026): cálculo do `ValidadorDvContaCorrente` transcrito em
  `leiautes/irpf2026/dv_conta.py` (17 bancos com regra, tamanhos de `bancos_calculo_dv.xml`, tabelas de
  agências do Nordeste e do Banese). Como no programa, DV que não confere só gera **aviso** no log
  (o bem é gravado). DV do roteiro geral e do exemplo corrigido (BB 98765 → 4).
- [x] Roteiro `tests/manual/dv_conta/` confirmado no programa em 19/11/2026: as 17 contas "válidas"
  (uma por banco) sem nenhum aviso e as 16 "inválidas" com o aviso "Dígito verificador da conta corrente
  inválido" em todas; regravados idênticos às saídas do bot. Algoritmos dos 17 bancos confirmados.
- [ ] Rendimentos de PJ de dependentes (32), isentos e exclusivos (23, 24, 83-89),
  dívidas (28), doações efetuadas (26, códigos 40-47, 80, 81).

### Fase 4c — comparação com IA (ADR 0026, decidido em 19/11/2026)

Fluxo: DBK → JSON (código) → IA compara com os PDFs anonimizados e devolve o JSON de alterações com
a referência `"dbk"` → o bot confere a referência e grava.

1. [x] Exportação DBK → JSON (19/11/2026): `exportar(arquivo)` nas 5 fichas, no formato do JSON de
   entrada, com `"dbk": {"chave": N}` (bens, dependentes, alimentandos) ou `{"item": N}` (fontes,
   pagamentos); campo em branco no DBK não sai (ex.: o tipo do dependente importado). Comando
   `uv run irpf-bot-2027-exportar ENTRADA.DBK SAIDA.json`. Ida e volta testada com os DBKs do programa
   das 5 fichas (`tests/test_exportacao.py`).
2. [x] Campo `"dbk"` no JSON de entrada (19/11/2026, ADR 0027), nas 5 fichas: a referência substitui a
   busca, depois de conferida (existe, mesmo tipo, mesmo identificador forte, sem duas referências ao
   mesmo item). Resolve o bem sem identificador e o pagamento no exterior com outro nome. Devolver o
   JSON exportado ao mesmo DBK não cria nem duplica nada (`tests/test_referencia.py`).
3. [ ] Prompt e JSON Schema da etapa de IA (fora do bot).
- Anonimização (software do escritório): mesmo código para o mesmo dado, normalizado antes; validar o
  enquadramento na LGPD com quem cuida disso (ADR 0026).

### Fase 5 — preparação para o IRPF 2027

O programa costuma sair entre o fim de fevereiro e março; adiante esta fase se a data se aproximar.

1. Script em `tools/` que lê a instalação do IRPF e gera os módulos do leiaute (registro 27,
   tabela de bens, países) e lista o que mudou em relação a 2026.
2. Documentar em `docs/` como as regras da tela foram extraídas (`javap -c -p` nas classes `Bem` e
   `PainelBensDetalhe`) — elas não podem ser geradas automaticamente.
3. `README.md` com uso, formato do JSON e estrutura.
4. Criar `leiautes/irpf2027/`, trocar os imports de `leiautes/atual.py`, gerar DBKs de teste no
   programa novo e rodar os testes.

### Depois

- JSON Schema gerado das regras, para a IA devolver o JSON no formato certo (saída estruturada).

## Decisões tomadas

As decisões de arquitetura, com contexto, alternativas e consequências, estão em
[docs/adr/](adr/README.md). Uma decisão nova vira um ADR no mesmo passo em que é implementada.

## Descobertas sobre o programa (testes de importação)

- Na importação, o programa **recalcula** totais (registro 20), contagens (T9), hash e controle do
  cabeçalho, **reatribui chaves repetidas** e **recria as linhas 37** a partir do registro 27.
  Aceitou até arquivo com LF em vez de CRLF. Mesmo assim, o bot grava tudo correto.
- `NR_ORDEM` do registro 37 é uma sequência única no arquivo (não reinicia por bem).
- Para grupos sem a pergunta titular/dependente (ex.: imóveis), o programa grava
  `TITULAR_DEPENDENTE` e `CPF_DONO` em branco.

## Descobertas no código do programa (javap, 11/11/2026)

Classes de `irpf.jar`, `lib-modulos/*.jar` e `lib/ppgd-*.jar`, lidas com `javap -c -p`.

- **Controle do cabeçalho IR** (`NR_CONTROLE`, posições 1235-1244): CRC32 de *nome do arquivo* +
  linha sem os 10 últimos caracteres. Nome = até 8 caracteres do nome sem extensão + extensão, em
  maiúsculas (ex.: `77039677.DBK`). `DocumentoAjusteTXT.atualizaHeader`/`preparaNomeArquivoParaCrc`,
  `RegistroTxt.calculaCRCHeader`. Implementado em `cabecalho.controle_cabecalho` (só para conferência)
  e confirmado nos DBKs de teste. `NR_HASH` do cabeçalho é um CRC acumulado da declaração.
- **Controles não são conferidos na restauração de .DBK**: `ImportadorTxt.restaurarDeclaracao` só
  valida os hashes (`validarHashsDeclaracao`, "Arquivo corrompido") de arquivos `.DEC`. Para `.DBK`,
  `validarHeader` confere só o CPF do cabeçalho e `SISTEMA = "IRPF"`; ele e `validarCRC` calculam os
  CRCs mas descartam o resultado. Por isso o programa aceitou LF, controle desatualizado e DBK
  renomeado. O bot continua gravando os controles das linhas corretos.
- **`IN_CRIT_OBRIGAT`** (`DeclaracaoIRPF.detalhaObrigatoriedadeEntregaAjuste`): soma, em decimal, de
  1 rendimentos tributáveis acima do limite · 2 isentos + exclusivos acima do limite · 4 renda
  variável · 8 ganho de capital com imposto · 16 venda de imóvel com reaplicação · 32 bens acima do
  limite · 64 receita rural acima do limite · 128 retorno ao país · 256 atualização de valor de bem ·
  512 prejuízo rural a compensar · 1024 lucros e dividendos no exterior · 2048 aplicação financeira no
  exterior com lucro · 4096 prejuízo da Lei 14.754. Calculado na gravação a partir dos dados; o bot
  não precisa mexer.
- **`NR_CONTA`** (`Bem.getContaFormatadaTxt`): Caixa (banco 104) com operação = operação com 3 dígitos
  + conta com 8 dígitos (zeros à esquerda); Caixa sem operação = conta com 12 dígitos; demais bancos =
  conta sem espaços nas pontas. `NR_BANCO` só é gravado se o banco foi informado.
- **Negativos** (`CampoTXT.set(Valor)`/`getTxt`): `-` na primeira posição e os dígitos com zeros à
  esquerda (-123,45 em N13,2 = `-000000012345`). O `Campo.formatar` do bot já produz esse formato.
- **Registro 27, por `ConversorObjetosIRPF2Registros.montarFichaBem`**: veículo (02/01), no Brasil ou
  no exterior, grava o registro do bem em `NR_RENAVAN`; imóvel fora do Brasil grava a cidade em
  `NM_MUNICIP` e o CEP/ZIP em `NR_CEP` (confirma o que o bot já faz).
- **Registro 59** (`REG_PERCENTUAL_BEM`): percentual de cada bem por herdeiro (chave do bem, chave do
  herdeiro, percentual N5,2). Só existe na Declaração Final de Espólio.

## Pendências em aberto

- ZIP do exterior com letras: o bot passa o CEP por `so_digitos`; falta ver se o programa aceita
  letras em `NR_CEP` quando o imóvel é no exterior.
- Registro 59 (Declaração Final de Espólio): mapeado, não implementado (só se houver cliente espólio).
