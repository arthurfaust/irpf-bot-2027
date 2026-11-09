from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(__file__).resolve().parent / "dados"

# DBKs gerados pelo próprio programa IRPF 2026 (cópias de segurança).
DBKS_DO_PROGRAMA = [DADOS / "entrada.DBK", DADOS / "programa_com_imovel.DBK"]


def ler_linhas(caminho: Path) -> list[str]:
    return caminho.read_bytes().decode("latin-1").split("\r\n")


def linhas_27() -> list[tuple[str, str]]:
    """(identificação para o pytest, linha) de todas as linhas 27 dos DBKs do programa."""
    casos = []
    for dbk in DBKS_DO_PROGRAMA:
        for numero, linha in enumerate(ler_linhas(dbk), start=1):
            if linha.startswith("27"):
                casos.append((f"{dbk.stem}:linha{numero}", linha))
    return casos


@pytest.fixture
def dados() -> Path:
    return DADOS
