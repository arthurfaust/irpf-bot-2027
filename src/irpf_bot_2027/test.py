import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
print(f'Raiz: {ROOT_DIR}')

load_dotenv(ROOT_DIR / 'config' / '.env')

raw_file = ROOT_DIR / os.environ['RAW_FILE']
new_file = ROOT_DIR / os.environ['OUTPUT_FILE']

COD_ITEM_INI = 0
COD_ITEM_FIM = 2
COD_ITEM_TAMANHO = 2
CPF_INI= 3
CPF_FIM = 14

def encontrar_bens() -> None:
    linhas_bens = []
    
    for i, linha in enumerate(linhas):
        
        if linha[COD_ITEM_INI:COD_ITEM_FIM] == '27': # Bem
            linhas_bens.append(i)
            
    return linhas_bens

with open(raw_file, "r", encoding="latin-1") as f:
    linhas = f.readlines()

linhas_bens = encontrar_bens()

linha_novo_bem = linhas_bens[-1] + 1

linhas.insert(linha_novo_bem, 'Novo bem aqui')

with open(new_file, "w", encoding="latin-1") as nf:
    nf.writelines(linhas)