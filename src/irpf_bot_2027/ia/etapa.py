"""
Etapa de IA: documentos do cliente + DBK -> JSON de entrada do bot (docs/adr/0026, 0028 e 0029).

Uso (no WSL, com o extra instalado: uv sync --extra ia):
    uv run irpf-bot-2027-ia --dbk ENTRADA.DBK --documentos PASTA_DOS_PDFS --saida CLIENTE.json

    1. exporta o DBK para JSON e o pseudonimiza (pseudonimizacao.py; a tabela fica só na memória);
    2. manda à IA o prompt (docs/ia/prompt.md), os documentos (já anonimizados pelo software do
       escritório) e o JSON do DBK, pedindo a saída no esquema docs/ia/esquema_ia.json;
    3. confere a resposta: o esquema da IA, desfaz os códigos, o esquema do bot e a validação de cada
       ficha. Havendo erro, as mensagens (sem dados do cliente) voltam à IA, até --tentativas vezes;
    4. grava o JSON com os dados reais, pronto para `uv run irpf-bot-2027`.

A credencial do provedor vem do config/.env (ex.: ANTHROPIC_API_KEY; veja config/.env.example) ou do
ambiente, que tem prioridade.

O log não mostra conteúdo: só contagens, nomes de etapas e as mensagens de erro do bot (que citam o
campo e o formato). O JSON gravado tem dados do cliente.
"""

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from irpf_bot_2027.config import RAIZ
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.esquema import gerar
from irpf_bot_2027.exportar import exportar_dbk
from irpf_bot_2027.fichas import FICHAS
from irpf_bot_2027.ia.provedores import PROVEDORES, TIPOS_DE_DOCUMENTO, ErroIA, Provedor
from irpf_bot_2027.ia.pseudonimizacao import desfazer, pseudonimizar

logger = logging.getLogger(__name__)

PROMPT = Path(__file__).resolve().parents[3] / "docs" / "ia" / "prompt.md"


def prompt_de_sistema() -> str:
    """O prompt é o que vem depois da primeira linha '---' de docs/ia/prompt.md (antes dela, notas
    para quem mantém o projeto)."""
    texto = PROMPT.read_text(encoding="utf-8")
    return texto.split("\n---\n", 1)[1].strip()


def montar_pedido(dbk_pseudonimizado: dict, documentos: list[Path]) -> str:
    nomes = "\n".join(f"- {caminho.name}" for caminho in documentos)
    return (f"Documentos do cliente (anexados acima, na ordem):\n{nomes}\n\n"
            f"JSON do DBK (a declaração como está hoje):\n```json\n"
            f"{json.dumps(dbk_pseudonimizado, ensure_ascii=False, indent=1)}\n```\n\n"
            "Devolva o JSON de alterações.")


def conferir(texto: str, tabela, cpf_declarante: str) -> tuple[dict | None, list[str]]:
    """Resposta da IA -> (JSON com os dados reais, erros). Os erros não têm dados do cliente."""
    import jsonschema
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        return None, [f"a resposta não é um JSON válido (linha {erro.lineno}, coluna {erro.colno})"]

    erros = [f"esquema: {'/'.join(map(str, e.absolute_path)) or '(raiz)'}: {e.validator} não atendido"
             for e in jsonschema.Draft202012Validator(gerar(anonimizado=True)).iter_errors(dados)]
    if erros:
        return None, erros

    reais, desconhecidos = desfazer(dados, tabela)
    if desconhecidos:
        return None, [f"o código {c} não existe no JSON do DBK; não invente códigos (deixe o campo de fora "
                      "e registre uma pendência)" for c in desconhecidos]

    erros = [f"esquema do bot: {'/'.join(map(str, e.absolute_path)) or '(raiz)'}: {e.validator} não atendido"
             for e in jsonschema.Draft202012Validator(gerar()).iter_errors(reais)]
    for ficha in FICHAS:
        itens = reais.get(ficha.CHAVE_JSON) or []
        if itens:
            _, erros_ficha = ficha.validar(itens, cpf_declarante)
            erros += [f"{ficha.NOME} > {erro}" for erro in erros_ficha]
    return (reais if not erros else None), erros


def executar(dbk: Path, documentos: list[Path], provedor: Provedor, tentativas: int = 3) -> dict:
    """Roda a etapa e devolve o JSON com os dados reais; levanta ErroIA se não chegar a um JSON válido."""
    arquivo = ArquivoDBK.ler(dbk)
    exportado = exportar_dbk(arquivo)
    pseudonimizado, tabela = pseudonimizar(exportado)
    logger.info("DBK exportado e pseudonimizado: %d código(s) na tabela local",
                len(tabela.reais))

    with provedor.sessao(documentos) as conversa:
        texto = conversa.iniciar(prompt_de_sistema(), montar_pedido(pseudonimizado, documentos),
                                 gerar(anonimizado=True))
        for tentativa in range(1, tentativas + 1):
            dados, erros = conferir(texto, tabela, arquivo.cpf_declarante)
            if dados is not None:
                logger.info("Resposta conferida na tentativa %d", tentativa)
                return dados
            logger.warning("Tentativa %d: %d erro(s) na resposta da IA", tentativa, len(erros))
            for erro in erros[:20]:
                logger.warning("  - %s", erro)
            if tentativa == tentativas:
                break
            texto = conversa.corrigir("O bot recusou o JSON. Corrija só o que foi apontado e devolva o JSON "
                                      "inteiro de novo:\n" + "\n".join(f"- {erro}" for erro in erros))
    raise ErroIA(f"a IA não chegou a um JSON válido em {tentativas} tentativa(s)")


def listar_documentos(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in TIPOS_DE_DOCUMENTO)


def main() -> None:
    parser = argparse.ArgumentParser(description="Etapa de IA: documentos + DBK -> JSON de entrada do bot.")
    parser.add_argument("--dbk", type=Path, required=True, help="DBK de entrada (o mesmo que o bot vai receber)")
    parser.add_argument("--documentos", type=Path, required=True,
                        help="pasta com os documentos anonimizados (.pdf, .txt, .md)")
    parser.add_argument("--saida", type=Path, required=True, help="JSON a gravar (tem dados do cliente)")
    parser.add_argument("--provedor", choices=sorted(PROVEDORES), default="claude")
    parser.add_argument("--modelo", help="modelo do provedor (padrão: o do provedor)")
    parser.add_argument("--tentativas", type=int, default=3, help="respostas da IA conferidas, no máximo")
    args = parser.parse_args()
    load_dotenv(RAIZ / "config" / ".env")       # credencial do provedor; o ambiente tem prioridade
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    documentos = listar_documentos(args.documentos)
    if not documentos:
        raise SystemExit("Nenhum documento .pdf, .txt ou .md na pasta indicada.")
    provedor = PROVEDORES[args.provedor](**({"modelo": args.modelo} if args.modelo else {}))
    try:
        dados = executar(args.dbk, documentos, provedor, args.tentativas)
    except ErroIA as erro:
        raise SystemExit(f"Etapa de IA: {erro}")
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    contagens = ", ".join(f"{f.CHAVE_JSON}: {len(dados.get(f.CHAVE_JSON) or [])}" for f in FICHAS)
    logger.info("JSON gravado: %s (%s; pendências: %d)", args.saida.name, contagens,
                len(dados.get("pendencias") or []))


if __name__ == "__main__":
    main()
