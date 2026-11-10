"""Configuração da execução, lida do config/.env (ou de variáveis de ambiente).

Variáveis:
    RAW_FILE     DBK de entrada (cópia de segurança do programa)           obrigatória
    OUTPUT_FILE  DBK gerado pelo bot                                       obrigatória
    CLIENT_DATA  JSON com os dados do cliente   (padrão: data/dados.example.json)
    LOG_LEVEL    DEBUG | INFO | WARNING | ERROR  (padrão: INFO)

Caminhos relativos são resolvidos a partir da raiz do projeto. Variáveis já definidas no
ambiente têm prioridade sobre o .env (é assim que os testes apontam para tests/dados/).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
NIVEIS_LOG = ("DEBUG", "INFO", "WARNING", "ERROR")

class ErroConfiguracao(Exception):
    """Configuração ausente ou inválida no .env."""

@dataclass(frozen=True)
class Config:
    arquivo_entrada: Path
    arquivo_saida: Path
    arquivo_dados: Path
    pasta_logs: Path
    nivel_log: str

def _obrigatoria(nome: str) -> str:
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise ErroConfiguracao(f"defina {nome} no config/.env (veja config/.env.example)")
    return valor

def carregar_config() -> Config:
    load_dotenv(RAIZ / "config" / ".env")

    nivel_log = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    if nivel_log not in NIVEIS_LOG:
        raise ErroConfiguracao(f"LOG_LEVEL inválido: {nivel_log!r}. Use um de: {', '.join(NIVEIS_LOG)}")

    return Config(
        arquivo_entrada=RAIZ / _obrigatoria("RAW_FILE"),
        arquivo_saida=RAIZ / _obrigatoria("OUTPUT_FILE"),
        arquivo_dados=RAIZ / os.environ.get("CLIENT_DATA", "data/dados.example.json"),
        pasta_logs=RAIZ / "logs",
        nivel_log=nivel_log,
    )
