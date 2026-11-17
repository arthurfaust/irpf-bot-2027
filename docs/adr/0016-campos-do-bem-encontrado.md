# 0016. O que muda num bem encontrado no DBK além da situação atual

- **Status:** Aceito (substitui em parte o 0006: "1 encontrado → atualiza só a situação atual")
- **Data:** 17/11/2026

## Contexto

Pelo ADR 0006, um bem do JSON encontrado no DBK só atualizava `VALOR_ATUAL`; o resto do JSON era
ignorado sem aviso. Os roteiros manuais mostraram três casos que passavam calados: discriminação nova,
código diferente (fundo informado como 07/03, lançado como 07/01) e campos que o DBK não tinha
(declaração antiga sem DV, sem CNPJ etc.).

Em ações, BDRs, fundos e criptoativos a discriminação costuma trazer a quantidade (ações, cotas,
unidades), que muda todo ano. Nos demais tipos (contas, imóveis, veículos...) a discriminação foi
escrita na declaração anterior e em geral continua valendo. Hoje a discriminação do JSON vem da IA;
no futuro a IA pode passar a montar a discriminação a partir da do ano anterior.

Decisão tomada pelo Arthur em 17/11/2026.

## Decisão

Num bem encontrado:

- **Situação atual:** sempre a do JSON. **Situação anterior:** nunca muda (aviso se diferente).
- **Discriminação:**
  - ações (03/01), BDRs/opções (04/04), fundos (grupo 07) e criptoativos (grupo 08): a do JSON
    substitui a do DBK (registrado no log, sem o texto);
  - demais tipos: fica a do DBK; se a do JSON for diferente, aviso.
  - A comparação ignora maiúsculas/minúsculas e espaços repetidos.
- **Grupo, código e país:** nunca mudam; diferença gera aviso.
- **Demais campos do JSON** que a tela mostra para o bem do DBK:
  - em branco no DBK → recebe o valor do JSON;
  - preenchido e diferente → fica o do DBK, com aviso.
  - Indicadores sim/não (bolsa, usufruto, autocustodiante, conta pagamento) com 0 = "Não" contam como
    preenchidos; "registrado em cartório" e "unidade da área" contam como vazios quando valem 2
    (não informado).
  - A comparação ignora o formato: números pelo valor; textos em maiúsculas, só letras e números,
    sem zeros à esquerda (conta da Caixa com ou sem zeros, "PT-ABC" e "PTABC").
- Os bens atualizados com alguma diferença entram em `Resultado.conferir` e numa linha "CONFERIR" do
  relatório. Os avisos citam o caminho do campo no JSON (ex.: `conta.dv`), nunca o conteúdo.

## Alternativas consideradas

- Manter sempre a discriminação do DBK e avisar: seguro, mas exigiria corrigir à mão a quantidade de
  toda ação, fundo e cripto, todo ano.
- Substituir sempre a discriminação pela do JSON: trocaria o texto revisado do ano anterior de contas,
  imóveis e veículos por um texto gerado pela IA.
- Só avisar também nos campos em branco: deixaria pendências que o JSON já sabe resolver.

## Consequências

- Os roteiros manuais de fundos e bolsa passam a substituir a discriminação; os de contas e veículos
  continuam mantendo a do DBK, agora com aviso.
- Quando a IA passar a montar a discriminação, rever a lista de tipos que usam a do JSON.
- O bloco `exterior` (rendimento e imposto do ano) terá campos anuais que devem ser sempre os do JSON;
  tratar no ADR desse bloco.
