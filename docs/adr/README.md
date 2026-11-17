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
| [0006](0006-busca-e-atualizacao-de-bens.md) | Procurar o bem no DBK e atualizar em vez de lançar | Substituído em parte por 0016 |
| [0007](0007-chave-da-cripto-e-chave-incompleta.md) | Chave da cripto e salvaguarda de chave incompleta | Aceito |
| [0008](0008-tipos-barrados-ate-ter-bloco.md) | Tipos de bem barrados até o JSON ter o bloco deles | Substituído por 0010, 0012 e 0014 |
| [0009](0009-busca-so-nos-bens-da-entrada.md) | A busca olha só os bens do DBK de entrada | Aceito |
| [0010](0010-bloco-conta.md) | Bloco `conta` libera poupança e conta corrente | Aceito |
| [0011](0011-chave-da-conta.md) | Chave da busca de poupança e conta corrente | Aceito |
| [0012](0012-bloco-bolsa.md) | Bloco `bolsa` com a pergunta "Negociados em Bolsa?" obrigatória | Aceito |
| [0013](0013-chave-das-acoes.md) | Chave da busca de ações e de ativos negociados em bolsa | Aceito |
| [0014](0014-bloco-veiculo.md) | Bloco `veiculo` libera veículo, aeronave e embarcação | Aceito |
| [0015](0015-chave-dos-bens-moveis.md) | Chave da busca de veículo, aeronave e embarcação | Substituído em parte por 0018 |
| [0016](0016-campos-do-bem-encontrado.md) | O que muda num bem encontrado no DBK além da situação atual | Aceito |
| [0017](0017-bloco-exterior.md) | Bloco `exterior`: valores do ano das aplicações e dividendos no exterior | Aceito |
| [0018](0018-busca-dos-bens-no-exterior.md) | Busca dos bens no exterior | Aceito |

Para um ADR novo, copie [modelo.md](modelo.md), use o próximo número e acrescente a linha acima.
As decisões de 0002 a 0005 e 0008 foram tomadas até 10/11/2026 e registradas aqui em 11/11/2026, a
partir do `docs/plano.md`.
