#!/usr/bin/env bash
# Roda o roteiro geral (todas as fichas) e gera as saídas dos três testes.
# Uso, no WSL, na raiz do projeto:  bash tests/manual/geral/rodar.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
M=tests/manual/geral
N=77039677008-IRPF-A-2026-2025-ORIGI.DBK

# base: o DBK vazio dos roteiros sem o pagamento vazio (código 02) que ele traz
mkdir -p "$M/base" "$M/importada"
uv run python - <<'PY'
from pathlib import Path
from irpf_bot_2027.dbk import ArquivoDBK
arquivo = ArquivoDBK.ler(Path("tests/manual/77039677008-IRPF-A-2026-2025-ORIGI.DBK"))
arquivo.linhas = [l for l in arquivo.linhas if not l.startswith("26")]
arquivo.gravar(Path("tests/manual/geral/base/77039677008-IRPF-A-2026-2025-ORIGI.DBK"))
PY
# importada: declaração importada do IRPF 2025 (dependente, alimentanda e 7 pagamentos sem valores)
cp tests/dados/pagamentos_importados.DBK "$M/importada/$N"

for teste in teste1_inserir teste2_repetir teste3_importada; do
  case $teste in
    teste1_inserir)   entrada=$M/base/$N ;;
    teste2_repetir)   entrada=$M/teste1_inserir/$N ;;
    teste3_importada) entrada=$M/importada/$N ;;
  esac
  echo "===== $teste"
  RAW_FILE=$entrada OUTPUT_FILE=$M/$teste/$N CLIENT_DATA=$M/$teste/entrada.json uv run irpf-bot-2027 2>&1 \
    | cut -d"|" -f4-
done

# rodar o mesmo JSON duas vezes não pode criar linhas
uv run python - <<'PY'
from collections import Counter
from pathlib import Path
from irpf_bot_2027.dbk import ArquivoDBK
M = Path("tests/manual/geral")
def tipos(teste):
    return Counter(l[:2] for l in ArquivoDBK.ler(M / teste / "77039677008-IRPF-A-2026-2025-ORIGI.DBK").linhas)
iguais = tipos("teste1_inserir") == tipos("teste2_repetir")
print("teste2 com as mesmas linhas do teste1:", "sim" if iguais else "NÃO")
PY
