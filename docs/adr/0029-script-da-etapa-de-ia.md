# 0029. Script da etapa de IA: provedor trocável e pseudonimização própria do DBK

- **Status:** Aceito
- **Data:** 19/11/2026

## Contexto

O ADR 0026 previa que o software de anonimização do escritório trocaria os dados sensíveis dos PDFs
por códigos estáveis (o mesmo CPF vira sempre o mesmo código), e que o JSON do DBK seria anonimizado
do mesmo jeito, para a IA casar os dois. O PDF de exemplo que o software devolve (confirmação de
corretora, 19/11/2026) mostra outra coisa: o dado é **apagado** (tarja ou espaço vazio), não trocado
por código. Não há código para casar com o DBK.

Falta também o programa que faz a chamada: monta o pedido, envia os documentos, confere a resposta,
devolve os erros à IA e desfaz a anonimização. O escritório quer poder trocar de provedor de IA.

## Decisão

1. Comando `uv run irpf-bot-2027-ia --dbk ENTRADA.DBK --documentos PASTA_OU_ARQUIVOS --saida SAIDA.json`
   (`src/irpf_bot_2027/ia/`), com dependências num extra opcional (`uv sync --extra ia`): o bot em si
   continua sem depender de IA.
2. **Pseudonimização própria do JSON do DBK** (`ia/pseudonimizacao.py`): o script troca CPFs, nomes de
   pessoas físicas, contas, Renavam, endereços, IPTU, processos e números dentro de textos por códigos
   (`CPF_0001`, `NOME_0002`, `CONTA_0001`, `NUM_0004`) e guarda a tabela **só na memória**. A IA copia os
   códigos nos itens que casam; o script os desfaz antes de entregar o JSON. CNPJ e nomes de empresa
   ficam abertos (ADR 0026). Código que não está na tabela é erro devolvido à IA.
3. O casamento com o DBK se faz pelo que sobrou nos documentos (instituição, natureza, ativo, datas,
   valores, situação anterior). Item novo cujo identificador foi apagado sai sem o campo e vira
   pendência; o bot aponta o campo obrigatório e o contador completa.
4. **Provedor trocável** (`ia/provedores.py`): a etapa só conhece `Provedor.sessao(documentos)` e
   `Conversa.iniciar/corrigir`. Um provedor novo é uma subclasse registrada em `PROVEDORES`. O primeiro
   é o Claude: modelo `claude-opus-5-5`, raciocínio adaptativo, esforço `high`, saída estruturada com
   `docs/ia/esquema_ia.json` (sem as restrições de tamanho, que a API não aceita e são conferidas
   localmente), documentos pela Files API com expiração de 1 hora e exclusão no fim da sessão, e o
   *fallback* do servidor para recusas de segurança habilitado.
5. **Conferência e correção automática** (`ia/etapa.py`): a resposta passa pelo esquema da IA, pela
   troca dos códigos, pelo esquema do bot e pela validação de cada ficha; os erros (sem dados do
   cliente) voltam à mesma conversa, até 3 tentativas. Só um JSON aprovado é gravado.

## Alternativas consideradas

- Pedir ao software de anonimização que gere códigos estáveis: depende de outro fornecedor e não
  resolve o DBK; a pseudonimização do DBK é nossa de qualquer jeito.
- Mandar o DBK sem anonimizar: enviaria CPFs e nomes de dependentes ao provedor, contra o ADR 0026.
- Gravar a tabela de códigos em disco: mais um arquivo com dados do cliente para proteger; como a
  conversa toda acontece num processo só, a memória basta.
- SDK de vários provedores (camada genérica): mais uma dependência para um provedor só; a interface
  própria tem dois métodos.

## Consequências

- Substitui a parte do ADR 0026 que supunha documentos com códigos; o resto dele vale.
- A IA não confirma a identidade de pessoas físicas pelos documentos: o casamento de dependentes e
  pagamentos a pessoas físicas depende do contexto (tipo, valores, instituição). Os testes com
  documentos reais anonimizados dirão se isso basta; se não, a saída vira pendência, não chute.
- Cada execução gasta créditos da API; o log mostra os tokens usados. Testes automatizados usam um
  provedor falso e nunca chamam a API.
- Lotes grandes de documentos podem passar do limite de saída; o script avisa ("divida os documentos em
  lotes") em vez de gravar um JSON cortado.
