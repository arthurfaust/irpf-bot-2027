# Teste manual: busca de criptoativos (ADR 0007)

Confere no programa IRPF 2026 a busca de cripto e a salvaguarda de chave incompleta. Declaração de
teste (CPF fictício 770.396.770-08), CNPJs fictícios com dígitos válidos.

```
cripto/
├── entrada.dbk          declaração "do ano anterior": a de tests/dados + ETH e USDT (ver abaixo)
├── teste1/              atualizar, lançar novo e chave incompleta
│   ├── entrada.json
│   └── saida.dbk
└── teste2/              dois bens do JSON para o mesmo lançamento e situação anterior divergente
    ├── entrada.json
    └── saida.dbk
```

Os dois testes partem do mesmo `entrada.dbk`. Cripto que já está nele:

| Chave | Bem | Custódia | 31/12/2024 | 31/12/2025 |
|---|---|---|---|---|
| 7 | 08/01 BTC | autocustodiante | 1.000,00 | 2.000,00 |
| 10 | 08/02 ETH | corretora X (11.222.333/0001-81) | 3.000,00 | 3.000,00 |
| 11 | 08/03 USDT | não autocustodiante, **CNPJ em branco** (simula declaração antiga) | 500,00 | 500,00 |

## Nome do arquivo para restaurar

A janela "Restaurar cópia de segurança" só mostra arquivos com o nome
`77039677008-IRPF-A-2026-2025-ORIGI.DBK`. Antes de restaurar, copie o DBK com esse nome:

```bash
mkdir -p /tmp/irpf-importar && cp tests/manual/cripto/teste1/saida.dbk /tmp/irpf-importar/77039677008-IRPF-A-2026-2025-ORIGI.DBK
```

No programa, abra a pasta `\\wsl.localhost\ubuntu\tmp\irpf-importar`. Troque `teste1/saida.dbk` pelo arquivo
que quiser conferir (inclusive o `entrada.dbk`).

## Teste 0 (opcional): o programa aceita o `entrada.dbk`?

Restaure o `entrada.dbk`. O USDT da chave 11 deve aparecer sem o CNPJ do custodiante, como numa
declaração antiga. Se o programa recusar o arquivo, o teste 1 ainda vale, mas anote o erro.

## Teste 1

```bash
RAW_FILE=tests/manual/cripto/entrada.dbk OUTPUT_FILE=tests/manual/cripto/teste1/saida.dbk CLIENT_DATA=tests/manual/cripto/teste1/entrada.json uv run irpf-bot-2027
```

Relatório esperado: `2 atualizado(s), 2 novo(s), 1 para revisão, 4 do DBK sem atualização`; o USDT da
chave 11 aparece com "dados da chave em branco no DBK".

| Bem do JSON | Resultado | 31/12/2024 | 31/12/2025 no programa |
|---|---|---|---|
| 1. BTC carteira própria | atualiza a chave 7 | 1.000,00 | **7.000,00** |
| 2. ETH corretora X (`"eth"` minúsculo) | atualiza a chave 10 | 3.000,00 | **4.500,00** |
| 3. ETH corretora Z | novo | 0,00 | 1.200,00 |
| 4. USDT corretora X | **revisão**, não gravado (o USDT da chave 11 tem a chave em branco) | 500,00 | 500,00 (sem mudança) |
| 5. BTC corretora no exterior (país 249) | novo (sem busca) | 0,00 | 2.500,00 |

O prédio e os dois fundos no exterior não mudam. A discriminação dos bens atualizados continua a do DBK.

## Teste 2

```bash
RAW_FILE=tests/manual/cripto/entrada.dbk OUTPUT_FILE=tests/manual/cripto/teste2/saida.dbk CLIENT_DATA=tests/manual/cripto/teste2/entrada.json uv run irpf-bot-2027
```

Relatório esperado: `1 atualizado(s), 0 novo(s), 2 para revisão, 5 do DBK sem atualização`, e o aviso
de situação anterior divergente no bem 3.

| Bem do JSON | Resultado | No programa |
|---|---|---|
| 1 e 2. ETH corretora X, duas vezes | **revisão**, os dois não gravados | ETH da chave 10 continua 3.000,00 / 3.000,00 |
| 3. BTC carteira própria, situação anterior 9.999,99 | atualiza a chave 7 | **1.000,00** / **8.000,00** (a situação anterior do DBK é mantida) |

Nenhum bem novo; nenhum bem repetido.
