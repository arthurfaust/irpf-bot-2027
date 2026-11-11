# 0002. Gravar direto no DBK e deixar o programa recalcular

- **Status:** Aceito
- **Data:** até 10/11/2026 (registrado em 11/11/2026)

## Contexto

O objetivo é lançar a declaração sem digitar ficha por ficha no programa IRPF. O programa grava e
restaura cópias de segurança `.DBK`: texto Latin-1 de largura fixa, uma linha por registro, leiaute
oficial em `irpf.jar!/mapeamentoTxt.xml`. Testes de importação mostraram que, ao restaurar, o programa
recalcula os totais (registro 20), as contagens (T9), o hash e o controle do cabeçalho, reatribui
chaves repetidas e recria as linhas 37 a partir do registro 27. Lendo o código (`javap`): na
restauração de `.DBK` só são conferidos o CPF do cabeçalho e `SISTEMA = "IRPF"`.

## Decisão

O bot lê o DBK, altera ou insere as linhas das fichas (hoje, o registro 27) e grava um DBK novo, que é
restaurado no programa. Mesmo o programa recalculando, o bot grava tudo correto: controle CRC32 de
cada linha, CRLF, sem quebra depois da última linha, ordem dos registros do leiaute.

## Alternativas consideradas

- Automatizar a interface do programa (cliques e digitação): frágil e lenta.
- Gerar o arquivo `.DEC` de transmissão: tem hash conferido e é a entrega oficial; errar ali é pior.

## Consequências

- Depende do leiaute de cada ano (ver 0004) e de regras da tela lidas do programa.
- O teste byte a byte (`tests/test_saida_referencia.py`) e a importação manual no programa são a
  prova de que a saída está certa.
- O arquivo restaurável precisa se chamar `CPF-IRPF-A-AAAA-AAAA-ORIGI.DBK` (filtro da janela de
  restauração).
