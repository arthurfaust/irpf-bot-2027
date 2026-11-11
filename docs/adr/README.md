# Registros de decisão de arquitetura (ADRs)

Cada decisão de arquitetura do projeto fica num arquivo numerado, para saber **o que** foi decidido,
**por quê** e **o que isso implica**. Um ADR não é editado depois de aceito: se a decisão mudar,
escreva um novo ADR que o substitui e marque o antigo como "Substituído por NNNN".

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-registrar-decisoes-em-adrs.md) | Registrar decisões de arquitetura em ADRs | Aceito |
| [0002](0002-gravar-direto-no-dbk.md) | Gravar direto no DBK e deixar o programa recalcular | Aceito |
| [0003](0003-json-amigavel-com-conversor.md) | JSON amigável + conversor, em vez do formato do DBK | Aceito |
| [0004](0004-leiaute-isolado-em-atual.md) | Leiaute do ano isolado em `leiautes/atual.py` | Aceito |
| [0005](0005-validar-tudo-antes-de-gravar.md) | Validar tudo antes de gravar; CPF do JSON conferido | Aceito |
| [0006](0006-busca-e-atualizacao-de-bens.md) | Procurar o bem no DBK e atualizar em vez de lançar | Aceito |
| [0007](0007-chave-da-cripto-e-chave-incompleta.md) | Chave da cripto e salvaguarda de chave incompleta | Aceito |
| [0008](0008-tipos-barrados-ate-ter-bloco.md) | Tipos de bem barrados até o JSON ter o bloco deles | Aceito |

Para um ADR novo, copie [modelo.md](modelo.md), use o próximo número e acrescente a linha acima.
As decisões de 0002 a 0005 e 0008 foram tomadas até 10/11/2026 e registradas aqui em 11/11/2026, a
partir do `docs/plano.md`.
