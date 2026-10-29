import os
import json
from pathlib import Path
from dotenv import load_dotenv
from irpf_bot_2027.registros import Registro27

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / 'config' / '.env')

raw_file = ROOT_DIR / os.environ['RAW_FILE']
new_file = ROOT_DIR / os.environ['OUTPUT_FILE']
client_data = ROOT_DIR / 'data' / 'dados.example.json'

def encontrar_bens(linhas:list) -> list:
    linhas_bens = []
    for i, linha in enumerate(linhas):
        if Registro27.TIPO_REGISTRO.ler(linha) == '27': # bem
            linhas_bens.append(i)
    return linhas_bens

with open(raw_file, 'r', encoding='latin-1') as f:
    linhas = f.readlines()

with open(client_data, 'r', encoding='utf-8') as data:
    dados = json.load(data)

linhas_bens = encontrar_bens(linhas)
index_preenchimento = linhas_bens[-1] + 1

string = ' ' * Registro27.TAMANHO # str com 1251 espaços
string = Registro27.TIPO_REGISTRO.gravar(string, '27')
string = Registro27.CPF.gravar(string, '12345678900')
string = Registro27.CODIGO.gravar(string, dados['codigo'])
string = Registro27.EXTERIOR.gravar(string, 0)
string = Registro27.PAIS.gravar(string, dados['localizacao'])
string = Registro27.DISCRIMINACAO.gravar(string, dados['discriminacao'])
string = Registro27.VALOR_2024.gravar(string, dados['situacao2024'])
string = Registro27.VALOR_2025.gravar(string, dados['situacao2025'])
string = Registro27.USUFRUTO.gravar(string, dados['usufruto'])  

linhas.insert(index_preenchimento, string + '\r\n')

with open(new_file, 'w', encoding='latin-1') as nf:
    nf.writelines(linhas)
