# 0026. Comparação com IA a partir do DBK exportado para JSON

- **Status:** Aceito
- **Data:** 19/11/2026

## Contexto

A busca por código (ADRs 0006, 0013, 0016, 0018, 0019, 0020, 0021, 0023, 0024, 0025) decide com
segurança quando o item tem identificador forte: Renavam, IPTU/CIB/CEI, banco + agência + conta, CNPJ +
código de negociação, CPF/CNPJ da fonte, CPF do dependente ou do alimentando. Sem ele (bens dos grupos
02/04–99 e 99, aplicações no exterior, imóvel sem IPTU, fundos do mesmo CNPJ, pagamento no exterior
pelo nome), o item vai para revisão, e o contador decide à mão.

O JSON do cliente já é produzido por IA a partir dos PDFs, depois de um software próprio do escritório
anonimizar os dados sensíveis. A IA consegue comparar descrições ("Conta no Nubank" × "NU PAGAMENTOS -
CONTA CORRENTE"), o que o código não faz com segurança.

## Decisão

Fluxo (definido com o Arthur em 19/11/2026):

1. **DBK → JSON, por código** (este projeto): cada ficha exporta os itens do DBK no mesmo formato do
   JSON de entrada, com uma referência ao item (`"dbk": {"chave": N}` em bens, dependentes e
   alimentandos; `"dbk": {"item": N}`, a ordem na ficha, em fontes e pagamentos).
2. **PDFs + JSON do DBK → JSON de alterações, por IA** (fora do bot, na etapa que já gera o JSON): a IA
   recebe os documentos e o DBK exportado, os dois anonimizados, e devolve só o que entra ou muda,
   cada item indicando o item do DBK que atualiza (`"dbk"`) ou nenhum (novo). Não é um JSON "fundido":
   o que não vem no JSON continua no DBK como está (o bot nunca apaga).
3. **O bot confere e grava**: a referência só é aceita se o item existe, é do mesmo tipo e, havendo
   identificador forte nos dois lados, se ele é o mesmo; senão, revisão. Sem referência, vale a busca
   de hoje. A decisão da IA aparece no relatório.

Anonimização (pseudonimização), regras para a comparação continuar possível:
- o mesmo dado vira **sempre o mesmo código**, nos PDFs e no JSON do DBK, com a mesma tabela;
- normalizar antes de gerar o código (só dígitos, sem zeros à esquerda): o DBK grava a conta como
  "000012345678" e o extrato mostra "1234-5";
- sem máscara parcial ("***.456.789-**");
- o JSON volta aos dados reais (com a tabela, guardada só no escritório) antes de chegar ao bot.
- Mascarar todo dado de pessoa física (titular, dependentes, alimentandos, médicos, locadores, fontes
  PF), os identificadores que levam ao dono (endereço, IPTU, matrícula, Renavam, placa, banco + agência +
  conta) e o texto livre (discriminação, descrição). CNPJ (pessoa jurídica) e valores ficam abertos.
- Pela LGPD, pseudonimização reversível continua sendo dado pessoal (art. 13, §4º) e pagamentos de
  saúde são dado sensível (art. 5º, II): exige base legal e provedor de IA sem retenção/treino com os
  dados. A validar com quem cuida da LGPD no escritório (não é decisão técnica).

Ordem de implementação: (1) exportação DBK → JSON; (2) campo `dbk` no JSON de entrada e a conferência
do passo 3, com ADR próprio; (3) prompt e JSON Schema da etapa de IA.

## Alternativas consideradas

- Chamar a API de IA dentro do bot só para os itens em revisão: o bot passaria a depender de rede e
  de chave de API, e a IA seria chamada duas vezes (gerar o JSON e comparar). Fica como alternativa se
  a comparação na etapa de geração não bastar.
- A IA devolver um JSON fundido (DBK inteiro + alterações): cada item reescrito é uma chance de alterar
  o que não devia.
- Aceitar a referência da IA sem conferência: um casamento errado atualiza o bem errado, que é erro
  na declaração.

## Consequências

- Os ADRs de busca continuam valendo para quem não traz referência; o ADR do passo (2) os substituirá
  em parte.
- Toda ficha passa a exportar (`exportar(arquivo)`), além de validar/inserir/relatorio.
- A qualidade da comparação depende da anonimização seguir as regras acima; o software de anonimização
  é do escritório e fica fora deste projeto.
