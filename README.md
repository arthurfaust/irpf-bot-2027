Estrutura Atual

src/irpf_bot_2027/
├── main.py              ← orquestra: lê DBK → confere exercício → lê JSON → valida tudo → insere → grava
├── config.py, config_log.py
├── dbk/                 ← Campo, Registro, ArquivoDBK            (não muda entre anos)
├── comum/               ← conversões                             (não muda entre anos)
├── leiautes/
│   ├── atual.py         ← troca de ano numa linha
│   └── irpf2026/        ← cabeçalho, registro 27, tabela de códigos, regras
└── fichas/
    ├── __init__.py      ← FICHAS
    └── bens/            ← entrada, validação, ficha