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
- [ ] Demais tipos de bem; campos anuais (discriminação, quadros do exterior) na atualização.

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

`conta` (banco, agência, conta, DV, conta pagamento), `bolsa` (negociado, código de negociação),
`veiculo` (Renavam, registros de aeronave/embarcação), `exterior` (aplicação financeira e lucros e
dividendos; usar `numero(..., permite_negativo=True)` no rendimento ou perda). O bloco `exterior`
também gera linhas 37: confirmar num teste se o programa as recria a partir da 27 (o teste manual
indicou que sim).

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

- Outras fichas (rendimentos, dependentes, dívidas, pagamentos) em `fichas/`.
- JSON Schema gerado das regras, para a IA devolver o JSON no formato certo (saída estruturada).

## Decisões tomadas (e por quê)

- **JSON amigável + conversor** (`entrada.py`), em vez de JSON no formato do DBK: a IA escreve o que
  está no documento (`"m2"`, `true`), os códigos do DBK ficam só no código.
- **`leiautes/atual.py`** em vez de variável `LEIAUTE` no `.env`: com um leiaute só, a variável
  exigiria imports dinâmicos sem uso real. Trocar de ano = mudar os imports desse arquivo.
- **Nomes sem ano**: `VALOR_ANTERIOR`/`VALOR_ATUAL`, `situacao_anterior`/`situacao_atual`.
- **`cnpj_cpf`** no primeiro nível do bem para o CNPJ de ações, fundos, contas etc. (CPF/CNPJ do
  devedor nos créditos); a cripto usa `cripto.cnpj_custodiante`. Informar os dois é erro.
- **Situação anterior e atual são obrigatórias** no JSON (use `"0.00"`), para a IA não omitir
  um valor por engano.
- **Valores**: aceitos `"1234.56"` ou número do JSON; sem arredondamento escondido.
- **Conta corrente, poupança, veículo e embarcação no Brasil ficam barrados** até os blocos da
  fase 4, porque o programa exige banco/agência/conta e Renavam/registro.
- **`"cpf"` obrigatório no JSON e conferido com o CPF do declarante do DBK**; se faltar ou não bater,
  nada é gravado (evita gravar os dados de um cliente na declaração de outro).
- **"Negociados em bolsa?" não é exigido**: falta confirmar se o programa aceita o padrão "Não".
- **Imóvel no exterior**: só logradouro, área e unidade são exigidos (validador do programa para
  esse caso não lido em detalhe).

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
