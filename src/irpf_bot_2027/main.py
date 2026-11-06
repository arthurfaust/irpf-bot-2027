import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from irpf_bot_2027.registros import Registro27
from irpf_bot_2027.config_log import configurar_log
from irpf_bot_2027.tabela_bens import nome_codigo
from irpf_bot_2027.validacao import validar_bem
from irpf_bot_2027.regras import BRASIL, TITULAR_OU_DEPENDENTE, esta_na_tabela

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / 'config' / '.env')

raw_file = ROOT_DIR / os.environ['RAW_FILE']
new_file = ROOT_DIR / os.environ['OUTPUT_FILE']
client_data = ROOT_DIR / 'data' / 'dados.example.json'
log_dir = ROOT_DIR / 'logs'

configurar_log(log_dir)

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

logger.info("Arquivo de entrada: %s (%d linhas, %d bens)", raw_file.name, len(linhas), len(linhas_bens))
logger.info("Dados do cliente: %s (%d bens a inserir)", client_data.name, len(dados['bens']))

index_preenchimento = linhas_bens[-1] + 1
chave = proxima_chave(linhas, linhas_bens)

cpf = Registro27.CPF.ler(next(l for l in linhas if not l.startswith('IR')))

erros = []
campos_por_bem = []   # campos extras de cada bem, já convertidos (usados na gravação)
for numero, bem in enumerate(dados['bens'], start=1):
    campos, erros_bem = validar_bem(bem)
    campos_por_bem.append(campos)
    erros.extend(f"bem {numero}: {erro}" for erro in erros_bem)

if erros:
    logger.error('Nenhum bem foi inserido. %d erro(s) no JSON.', len(erros))
    for erro in erros:
        logger.error("  - %s", erro)
    raise SystemExit(1)

for bem, campos in zip(dados['bens'], campos_por_bem):
    exterior = 0 if str(bem['pais']) == BRASIL else 1
    tem_titular_dependente = esta_na_tabela(TITULAR_OU_DEPENDENTE, bem['grupo'], bem['codigo'])

    lancamento = Registro27.gravar_valores_padrao(cpf, tem_titular_dependente)
    lancamento = Registro27.GRUPO.gravar(lancamento, bem['grupo'])
    lancamento = Registro27.CODIGO.gravar(lancamento, bem['codigo'])
    lancamento = Registro27.PAIS.gravar(lancamento, bem['pais'])
    lancamento = Registro27.EXTERIOR.gravar(lancamento, exterior)
    lancamento = Registro27.DISCRIMINACAO.gravar(lancamento, bem['discriminacao'])
    lancamento = Registro27.VALOR_2024.gravar(lancamento, bem['situacao_2024'])
    lancamento = Registro27.VALOR_2025.gravar(lancamento, bem['situacao_2025'])
    lancamento = Registro27.USUFRUTO.gravar(lancamento, bem.get('usufruto', False))
    lancamento = Registro27.CHAVE.gravar(lancamento, chave)

    for nome, valor in campos.items():                 # campos dos blocos do JSON, já validados
        lancamento = getattr(Registro27, nome).gravar(lancamento, valor)

    lancamento = Registro27.gravar_cod_controle(lancamento)          # sempre por último

    linhas.insert(index_preenchimento, lancamento + '\r\n')
    logger.info("Bem %s/%s (%s) inserido na linha %d com chave %d", bem['grupo'], bem['codigo'], nome_codigo(bem['grupo'], bem['codigo']), index_preenchimento + 1, chave)
    logger.info("  campos extras gravados: %s", ", ".join(sorted(campos)) or "nenhum")
    
    index_preenchimento += 1
    chave +=1

with open(new_file, 'w', encoding='latin-1', newline='') as nf:
    nf.writelines(linhas)
    logger.info('Arquivo gravado: %s', new_file.name)
