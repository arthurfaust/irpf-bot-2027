# 0025. Ficha Alimentandos

- **Status:** Aceito
- **Data:** 18/11/2026

## Contexto

Quinta ficha do bot (registro 35, 331 posições). Os pagamentos de pensão e as despesas de alimentandos
(ADR 0021) dependem dela. A importação da declaração anterior traz o alimentando sem data de
nascimento e sem tipo de processo, o que gera pendências.

Do programa IRPF 2026 (classes `Alimentando`, `DecisaoJudicial`, `EscrituracaoPublica` e
validadores, lidas com `javap`): nome (mesma regra do dependente), residência, nascimento, "Alimentando
do" (CPF do titular ou de um dependente) e tipo de processo obrigatórios; CPF obrigatório para
residente no Brasil, sem repetir e diferente do titular, de dependente e do "Alimentando do"; tipo de
processo escritura pública (C), decisão judicial (J) ou ambos (A), com a data da lavratura ou da
decisão obrigatória e entre o nascimento e 31/12 do ano-calendário; CNPJ do cartório com dígito.

Um DBK gravado pelo programa em 18/11/2026 com 3 alimentandos (`tests/dados/alimentandos_programa.DBK`)
confirmou o leiaute. No mesmo teste, a confirmação "Os alimentandos atendem aos requisitos?" foi
marcada, a cópia gravada e restaurada: a pendência voltou. **A confirmação não é gravada no DBK.**

## Decisão

- Lista `alimentandos` no JSON: `nome`, `cpf`, `data_nascimento`, `residente` ("brasil"/"exterior"),
  `alimentando_de` (CPF) e os blocos `decisao_judicial` e/ou `escritura_publica`, cada um com `data` e
  os campos opcionais da tela. O tipo de processo sai dos blocos informados.
- CPF obrigatório também para residente no exterior (escolha do projeto): é a chave da busca e da
  ligação com os pagamentos.
- Busca pelo CPF, igual à dos dependentes (ADR 0024): campo em branco no DBK recebe o do JSON (é o caso
  da importação), diferente fica e gera aviso; 2 ou mais → revisão; CPF de dependente do DBK, ou
  "Alimentando do" que não é o titular nem um dependente do DBK → revisão.
- `FICHAS = (rendimentos_pj, dependentes, alimentandos, pagamentos, bens)`.
- Sempre que o DBK tiver alimentandos, o relatório lembra de marcar a confirmação no programa.

## Alternativas consideradas

- Gravar a confirmação: ela não existe no leiaute do DBK.
- Aceitar alimentando sem CPF no exterior: o pagamento da pensão (31, 34) não teria como achá-lo; fica
  para quando aparecer o caso.

## Consequências

- Toda declaração com alimentandos continua com a pendência da confirmação depois da restauração; o
  contador precisa marcá-la no programa.
- Código e nome do município do cartório vêm do JSON sem conferência com a tabela do programa, como nos
  imóveis.
- Falta o roteiro manual.
