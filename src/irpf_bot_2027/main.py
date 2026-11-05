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

def proxima_chave(linhas: list, linhas_bens: list) -> int:
    chaves = [int(Registro27.CHAVE.ler(linhas[i])) for i in linhas_bens]
    return max(chaves, default=0) + 1

with open(raw_file, 'r', encoding='latin-1', newline='') as f:
    linhas = f.readlines()

with open(client_data, 'r', encoding='utf-8', newline='') as data:
    dados = json.load(data)

linhas_bens = encontrar_bens(linhas)
index_preenchimento = linhas_bens[-1] + 1
chave = proxima_chave(linhas, linhas_bens)

cpf = Registro27.CPF.ler(next(l for l in linhas if not l.startswith('IR')))

for bem in dados['bens']:
    string = ' ' * Registro27.TAMANHO  # str com 1251 espaços
    string = Registro27.TIPO_REGISTRO.gravar(string, '27')
    string = Registro27.CPF.gravar(string, cpf)
    string = Registro27.GRUPO.gravar(string, bem['grupo'])
    string = Registro27.CODIGO.gravar(string, bem['codigo'])
    string = Registro27.EXTERIOR.gravar(string, 0)
    string = Registro27.PAIS.gravar(string, bem['pais'])
    string = Registro27.DISCRIMINACAO.gravar(string, bem['discriminacao'])
    string = Registro27.VALOR_2024.gravar(string, bem['situacao_2024'])
    string = Registro27.VALOR_2025.gravar(string, bem['situacao_2025'])
    string = Registro27.USUFRUTO.gravar(string, bem.get('usufruto', False))
    string = Registro27.CHAVE.gravar(string, chave) 

    linhas.insert(index_preenchimento, string + '\r\n')
    print(f'Bem {bem['grupo']}/{bem['codigo']} inserido na linha {index_preenchimento + 1} com chave {chave}')
    
    index_preenchimento += 1
    chave +=1

with open(new_file, 'w', encoding='latin-1', newline='') as nf:
    nf.writelines(linhas)
