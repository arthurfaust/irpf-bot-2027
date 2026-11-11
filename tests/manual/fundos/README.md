# Teste manual: busca e atualização de fundos nacionais (fase 3)

Confere no programa IRPF 2026 os três caminhos da busca: fundo novo (0 encontrado), fundo
atualizado (1 encontrado) e situação anterior do DBK preservada. Tudo com a declaração de teste
(CPF fictício 770.396.770-08) e CNPJs fictícios com dígitos válidos.

O nome da saída é obrigatório: na janela "Restaurar cópia de segurança" o programa só mostra
arquivos `CPF-IRPF-A-2026-2025-ORIGI.DBK` (`FiltroCopiaSeguranca`). Por isso cada etapa grava numa
pasta própria.

## Etapa 1: lançar os fundos A e B (como se viessem da declaração anterior)

No WSL, na raiz do projeto (as variáveis da linha de comando têm prioridade sobre o `config/.env`):

```bash
mkdir -p tests/manual/fundos/saida/etapa1 tests/manual/fundos/saida/etapa2
RAW_FILE=tests/dados/entrada.DBK OUTPUT_FILE=tests/manual/fundos/saida/etapa1/77039677008-IRPF-A-2026-2025-ORIGI.DBK CLIENT_DATA=tests/manual/fundos/etapa1.json uv run irpf-bot-2027
```

Relatório esperado: `0 atualizado(s), 2 novo(s), 0 para revisão, 4 do DBK sem atualização`.

Restaure `saida/etapa1/77039677008-IRPF-A-2026-2025-ORIGI.DBK` no programa e confira na ficha Bens e Direitos:

| Bem | Grupo/código | CNPJ | 31/12/2024 | 31/12/2025 |
|---|---|---|---|---|
| Fundo A | 07/01 | 11.222.333/0001-81 | 10.000,00 | 12.000,00 |
| Fundo B | 07/01 | 11.444.777/0001-61 | 5.000,00 | 5.500,00 |

## Etapa 2: atualizar A e B e lançar C, partindo da saída da etapa 1

```bash
RAW_FILE=tests/manual/fundos/saida/etapa1/77039677008-IRPF-A-2026-2025-ORIGI.DBK OUTPUT_FILE=tests/manual/fundos/saida/etapa2/77039677008-IRPF-A-2026-2025-ORIGI.DBK CLIENT_DATA=tests/manual/fundos/etapa2.json uv run irpf-bot-2027
```

Relatório esperado: `2 atualizado(s), 1 novo(s), 0 para revisão, 4 do DBK sem atualização`, e um
aviso de que a situação anterior do bem 2 difere da do DBK.

Restaure `saida/etapa2/77039677008-IRPF-A-2026-2025-ORIGI.DBK` e confira:

| Bem | 31/12/2024 | 31/12/2025 | O que mostra |
|---|---|---|---|
| Fundo A | 10.000,00 | **15.000,00** | atualizado; a discriminação continua a da etapa 1 (a "DESCRICAO NOVA" do JSON é ignorada) |
| Fundo B | **5.000,00** | **6.000,00** | atualizado; o 9.999,99 do JSON não substitui a situação anterior do DBK |
| Fundo C | 0,00 | 3.000,00 | lançado como novo (CNPJ 33.444.555/0001-81) |

Os bens que já estavam na declaração de teste (prédio, bitcoin e dois fundos no exterior) não mudam,
e não pode haver fundo A ou B repetido.
