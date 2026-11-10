# Plano do irpf-bot-2027

Situação em 10/11/2026 (último commit: `b22cdf0`). 185 testes passando.

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

1. Decidir por qual tipo de bem começar. Conta corrente/poupança têm a chave mais confiável
   (banco + agência + conta), mas dependem do bloco `conta` (fase 4). Alternativas já suportadas
   no JSON: imóvel (IPTU/matrícula), cripto (código + custodiante), ações/fundos (CNPJ).
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

## Pendências em aberto

- Algoritmo do código de controle do cabeçalho IR (posições 1235-1244); não é CRC32 simples.
- Testar se o programa aceita uma linha 27 com código de controle errado.
- Formato do `NR_CONTA` para a Caixa (operação) e valores negativos no DBK.
- Significado dos bits de `IN_CRIT_OBRIGAT` (cabeçalho).
- Destino do "Registro de Veículo" de veículo no exterior (provavelmente `NR_RENAVAN`) e endereço de
  imóvel no exterior (cidade/ZIP em `NM_MUNICIP`/`NR_CEP`): inferidos, não confirmados.
- Conferir o CPF do JSON (`cpf`) com o CPF do DBK (hoje a chave é aceita, mas não conferida).
- Declaração Final de Espólio (bem a inventariar, registro 59) não foi mapeada.
