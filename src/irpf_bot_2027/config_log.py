import logging
from datetime import datetime
from pathlib import Path

FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"

def configurar_log(pasta_logs: Path, nivel: str = "INFO") -> None:
    pasta_logs.mkdir(exist_ok=True)
    arquivo = pasta_logs / f"execucao_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"

    logging.basicConfig(
        level=nivel,
        format=FORMATO,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),                            # terminal
            logging.FileHandler(arquivo, encoding="utf-8"),     # arquivo da execução
        ],
    )