import os
import json
from pathlib import Path
from dotenv import load_dotenv
from irpf_bot_2027.registros import Registro27
from irpf_bot_2027.tabela_bens import codigo_existe, nome_codigo

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

erros =[]
for numero, bem in enumerate(dados['bens'], start=1):
    if not codigo_existe(bem['grupo'], bem['codigo']):
        erros.append(f"bem {numero}: grupo/código {bem['grupo']}/{bem['codigo']} não existe")

if erros:
    print('Nenhum bem foi inserido. Corrija o JSON:')
    for erro in erros:
        print(' -', erro)
    raise SystemExit(1)

for bem in dados['bens']:
    exterior = 0 if str(bem['pais']) == '105' else 1

    lancamento = Registro27.gravar_valores_padrao(cpf)
    lancamento = Registro27.GRUPO.gravar(lancamento, bem['grupo'])
    lancamento = Registro27.CODIGO.gravar(lancamento, bem['codigo'])
    lancamento = Registro27.PAIS.gravar(lancamento, bem['pais'])
    lancamento = Registro27.EXTERIOR.gravar(lancamento, exterior)
    lancamento = Registro27.DISCRIMINACAO.gravar(lancamento, bem['discriminacao'])
    lancamento = Registro27.VALOR_2024.gravar(lancamento, bem['situacao_2024'])
    lancamento = Registro27.VALOR_2025.gravar(lancamento, bem['situacao_2025'])
    lancamento = Registro27.USUFRUTO.gravar(lancamento, bem.get('usufruto', False))
    lancamento = Registro27.CHAVE.gravar(lancamento, chave)
    lancamento = Registro27.gravar_cod_controle(lancamento)          # sempre por último

    linhas.insert(index_preenchimento, lancamento + '\r\n')
    print(f"Bem {bem['grupo']}/{bem['codigo']} ({nome_codigo(bem['grupo'], bem['codigo'])}) inserido na linha {index_preenchimento + 1} com chave {chave}")
    
    index_preenchimento += 1
    chave +=1

with open(new_file, 'w', encoding='latin-1', newline='') as nf:
    nf.writelines(linhas)
