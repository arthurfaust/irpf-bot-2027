"""
Exporta um DBK para JSON, no formato do JSON de entrada do bot (docs/adr/0026).

Uso (no WSL):  uv run irpf-bot-2027-exportar ENTRADA.DBK SAIDA.json

O JSON tem o "cpf" do declarante e uma lista por ficha (as chaves de fichas/FICHAS), cada item com a
referência ao item do DBK em "dbk". É a entrada da etapa de IA, que compara o DBK com os documentos
do cliente; o arquivo tem dados do cliente e deve passar pela anonimização antes de sair do escritório.
O log mostra só quantos itens cada ficha exportou.
"""

import argparse
import json
import logging
from pathlib import Path

from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import FICHAS

logger = logging.getLogger(__name__)


def exportar_dbk(arquivo: ArquivoDBK) -> dict:
    dados = {"cpf": arquivo.cpf_declarante}
    for ficha in FICHAS:
        dados[ficha.CHAVE_JSON] = ficha.exportar(arquivo)
    return dados


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta um DBK do IRPF para o JSON do bot.")
    parser.add_argument("entrada", type=Path, help="arquivo .DBK")
    parser.add_argument("saida", type=Path, help="arquivo .json a gravar")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    dados = exportar_dbk(ArquivoDBK.ler(args.entrada))
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    for ficha in FICHAS:
        logger.info("%s: %d item(ns)", ficha.NOME, len(dados[ficha.CHAVE_JSON]))
    logger.info("JSON gravado: %s", args.saida.name)


if __name__ == "__main__":
    main()
