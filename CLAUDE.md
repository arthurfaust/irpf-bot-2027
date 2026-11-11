# irpf-bot-2027

Bot que insere lançamentos da declaração de IRPF direto no arquivo `.DBK` (cópia de segurança do
programa IRPF da Receita), a partir de um JSON com os dados do cliente. Hoje cobre a ficha Bens e
Direitos (registro 27) com o leiaute do IRPF 2026; o alvo final é o IRPF 2027.

Plano, decisões e pendências: [docs/plano.md](docs/plano.md). Leia antes de começar uma tarefa.

## Regras de trabalho

- **Os commits são do Arthur.** Não faça commit nem push; ao fim de cada passo, sugira a mensagem
  (padrão `tipo(escopo): descrição`, em português).
- Trabalhe em **passos pequenos**: implemente, rode os testes, pare para revisão.
- Converse e documente em **português**. Código, nomes e docstrings também em português.
- **Não entre em pastas com dados de clientes**: `data/` (exceto `dados.example.json`), `raw/`,
  `gold/`, `logs/`, e as pastas `aplicacao/dados`, `gravadas/` e `transmitidas/` da instalação do IRPF.
- **Nunca registre dados do cliente** (CPF, discriminação, valores) em logs ou mensagens de erro.
  Mensagens citam o campo e o formato esperado, não o conteúdo.

## Como rodar (no WSL)

```bash
uv run pytest            # testes; rode antes de sugerir qualquer commit
uv run irpf-bot-2027     # executa com os caminhos do config/.env
```

`config/.env` define `RAW_FILE`, `OUTPUT_FILE`, `CLIENT_DATA` e `LOG_LEVEL` (veja `config/.env.example`).
Chamado pelo Windows (`wsl.exe ... bash -lc '...'`), o `$?` sempre aparece como 0; confira códigos de
saída pelos testes.

## Rede de segurança

`tests/test_saida_referencia.py` roda o bot com `tests/dados/entrada.DBK` + `tests/dados/bens.json` e
compara a saída **byte a byte** com `tests/dados/esperado.DBK` (arquivo importado com sucesso no
programa). Refatorações não podem mudar essa saída. Se uma mudança de comportamento for intencional,
gere o novo `esperado.DBK`, importe no programa para conferir e avise o Arthur.

Os DBKs em `tests/dados/` são de uma declaração de teste (CPF fictício 770.396.770-08).

## Estrutura atual

```
src/irpf_bot_2027/
├── main.py           orquestra: lê DBK → confere exercício → lê JSON → valida tudo → insere → grava
├── config.py         .env;  config_log.py: logs no terminal e em logs/
├── dbk/              genérico, não muda entre anos: Campo, Registro (base), ArquivoDBK
├── comum/            conversões (sim/não, dígitos, datas, números) e normalização de texto
├── leiautes/
│   ├── atual.py      ÚNICO ponto de importação do leiaute (troca de ano = mudar os imports daqui)
│   └── irpf2026/     cabeçalho, registro 27, tabela de grupos/códigos, países, regras da tela
└── fichas/
    ├── __init__.py   FICHAS = (bens,): cada ficha expõe NOME, CHAVE_JSON, validar(), inserir()
    └── bens/         entrada.py (JSON → campos), validacao.py, ficha.py (montagem e inserção)
tools/visualizador_dbk.html   abre um DBK e mostra os campos de cada linha
```

Para uma ficha nova: subpacote em `fichas/` com a mesma forma de `bens/` + incluir em `FICHAS`.

## Formato do DBK (confirmado em arquivos do programa)

- Texto **Latin-1**, linhas separadas por **CRLF**, **sem CRLF depois da última linha** (T9).
  O `ArquivoDBK` preserva isso; nunca leia/grave em modo texto sem `newline=""`.
- Largura fixa; posições começam em 1. Tipo `N`: zeros à esquerda, decimais implícitas.
  Tipo `C`/`A`: espaços à direita, gravado em maiúsculas.
- Os 2 primeiros caracteres são o tipo do registro; posições 3-13 são o CPF do declarante (exceto IR).
- Últimos 10 caracteres de cada linha = CRC32 (zlib) do resto da linha (exceto o cabeçalho IR, cujo
  algoritmo inclui o nome do arquivo: ver `leiautes/irpf2026/cabecalho.py`). Gravar o controle é sempre a última alteração da linha.
- Datas em DDMMAAAA (alguns campos do leiaute usam AAAAMMDD: confira antes de reaproveitar).

## Origem das regras

Tudo em `leiautes/irpf2026/` veio da instalação do programa (`C:\Arquivos de Programas RFB\IRPF2026`):
`irpf.jar!/mapeamentoTxt.xml` (leiaute oficial de todos os registros), `lib/resources/*.xml` (tabelas)
e as classes `Bem` e `PainelBensDetalhe` (regras da tela, lidas com `javap`). Cada módulo diz a sua
origem na docstring; mantenha esse padrão ao acrescentar regras. O que não veio do programa deve ser
marcado como escolha do projeto ou como "confirmado em DBK".
