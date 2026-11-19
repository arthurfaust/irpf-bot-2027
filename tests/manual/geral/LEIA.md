# Roteiro geral

Um cliente com **todas as fichas que o bot cobre**, para conferir no programa que elas convivem no
mesmo DBK. **A cada ficha nova, acrescente itens dela nos três `entrada.json` e rode de novo.**

Rodar (no WSL, na raiz do projeto): `bash tests/manual/geral/rodar.sh`. O script gera a `base/`, copia
a `importada/` e grava a saída de cada teste na pasta dele, com o mesmo nome do DBK.

| Teste | Entrada | O que mostra |
|---|---|---|
| teste1_inserir | `base/` (DBK vazio sem o pagamento vazio) | tudo lançado como novo |
| teste2_repetir | saída do teste1, **mesmo JSON** | rodar duas vezes não duplica: fontes e pagamentos em revisão, dependentes e alimentandos encontrados, bens atualizados; o fundo no exterior (sem identificador) vai para revisão (ADR 0018). O script confere que o teste2 tem as mesmas linhas do teste1 |
| teste3_importada | `importada/` (declaração importada do IRPF 2025) | dependente recebe o tipo, alimentanda recebe nascimento e processo, os 7 pagamentos importados recebem os valores; fonte e conta novas |

No programa: restaure cada saída, marque "Estou ciente..." na ficha Alimentandos (não é gravado no
DBK) e confira **Verificar pendências**. Só devem sobrar as da identificação do contribuinte, o aviso
"Alimentando não relacionado a despesa dedutível" quando for o caso e, no teste3, nenhuma de
Dependentes, Alimentandos ou Pagamentos. Grave `regravado_testeN.DBK` na pasta de cada teste.

Fichas no roteiro: rendimentos de PJ do titular, dependentes, alimentandos, pagamentos, bens.
