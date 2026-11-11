# 0001. Registrar decisões de arquitetura em ADRs

- **Status:** Aceito
- **Data:** 11/11/2026

## Contexto

As decisões estavam numa lista curta no `docs/plano.md`, junto com andamento e pendências. A lista
não guardava as alternativas descartadas nem as consequências, e o plano muda a cada passo. O
projeto vai atravessar anos (IRPF 2026 → 2027) e ser retomado por sessões diferentes.

## Decisão

Cada decisão de arquitetura vira um arquivo numerado em `docs/adr/` (contexto, decisão, alternativas,
consequências). ADR aceito não é reescrito; uma mudança gera um ADR novo que substitui o anterior.
O `docs/plano.md` continua com andamento e pendências e aponta para os ADRs.

## Alternativas consideradas

- Manter a lista no plano: rápida, mas perde o "por quê" e o histórico.
- Registrar só nas mensagens de commit: espalhado e difícil de consultar.

## Consequências

- Toda decisão nova que afete estrutura, formato do JSON, o que é gravado no DBK ou a segurança dos
  dados do cliente ganha um ADR no mesmo passo em que é implementada.
- Docstrings podem citar o ADR (ex.: `docs/adr/0007`) em vez de repetir a justificativa.
