# 0028. Etapa de IA: prompt, esquemas gerados do código, origem e pendências

- **Status:** Aceito
- **Data:** 19/11/2026

## Contexto

Passo 3 do ADR 0026: definir o que a IA recebe e devolve. A IA não recebe um PDF só, mas **vários**
documentos do cliente (informes de rendimentos e de bancos, extratos de corretora, recibos, boletos,
documentos de veículos...), anonimizados, mais o JSON do DBK exportado. O mesmo bem ou fonte aparece em
mais de um documento, os recibos de um mesmo prestador precisam ser somados, e documentos podem se
contradizer.

O plano já previa "JSON Schema gerado das regras, para a IA devolver o JSON no formato certo".

## Decisão

- **Prompt** em `docs/ia/prompt.md` (português, prompt de sistema), com: o inventário dos documentos
  antes de escrever; um item por coisa, não por documento; pagamentos somados por beneficiário + código
  + quem recebeu; conflito entre documentos não é resolvido pela IA (vira pendência); critérios de
  casamento com o DBK e quando não usar `"dbk"`; o que copiar do DBK num item encontrado (situação
  anterior, discriminação fora de 03/01, 04/04, 07 e 08, campos preenchidos — ADR 0016); códigos de
  anonimização copiados como estão; o ciclo de correção com as mensagens de erro do bot.
- **Dois JSON Schemas gerados do código** (`src/irpf_bot_2027/esquema.py`, comando
  `uv run irpf-bot-2027-esquema docs/ia`), das mesmas tabelas e constantes que a validação usa:
  - `esquema_entrada.json`: o JSON que o bot recebe (dados reais);
  - `esquema_ia.json`: a saída da IA, igual, mas com CPF, CPF/CNPJ, telefone e identificadores dos bens
    aceitando o código da anonimização.
  O esquema descreve forma, códigos e formatos; as regras que dependem da combinação de campos (blocos
  por grupo/código, campos por código de pagamento) vão nas descrições e continuam com o bot.
  `tests/test_esquema.py` falha se o arquivo em `docs/ia/` não estiver em dia com o código, se o
  esquema recusar algo que o bot aceita ou aceitar o que ele recusa nos casos testados.
- **Campo `"origem"` em cada item** (opcional para o bot, exigido pelo prompt): a lista de
  `{"documento", "pagina"}` que sustenta o item. O bot só confere o formato; não grava nem registra no
  log (o nome do documento pode identificar o cliente).
- **Chave `"pendencias"` no topo do JSON**: o que a IA não decidiu sozinha, para o contador. O bot não
  grava nada com ela e o log só diz quantas são.
- As mensagens de erro do bot não têm dados do cliente; por isso podem voltar à IA para correção.

## Alternativas consideradas

- Um esquema escrito à mão: desatualiza na primeira regra nova; gerado do código, o teste acusa.
- Expressar no esquema todas as regras condicionais (if/then por grupo/código e por código de
  pagamento): esquema enorme e frágil; o bot já confere e explica o erro.
- Um JSON por documento, juntado depois por código: a junção (mesmo bem em dois documentos, recibos
  do mesmo prestador) é justamente o que precisa de julgamento; fica com a IA, que vê todos juntos.

## Consequências

- Mudou uma regra ou tabela do bot → rodar `uv run irpf-bot-2027-esquema docs/ia` (o teste lembra).
- A qualidade depende de a anonimização manter o mesmo código para o mesmo dado (ADR 0026).
- Falta escolher o provedor e o modelo, e o script que monta a chamada (documentos + JSON do DBK +
  prompt) e desfaz a anonimização; fica fora do bot.
