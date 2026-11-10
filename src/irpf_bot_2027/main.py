import json
import logging

from irpf_bot_2027.config import ErroConfiguracao, carregar_config
from irpf_bot_2027.config_log import configurar_log
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import CHAVES_JSON_CONHECIDAS, FICHAS
from irpf_bot_2027.leiautes.atual import verificar_exercicio

logger = logging.getLogger(__name__)

def main() -> None:
    try:
        config = carregar_config()
    except ErroConfiguracao as erro:
        raise SystemExit(f"Erro de configuração: {erro}")

    configurar_log(config.pasta_logs, config.nivel_log)

    # 1. Ler e conferir o DBK de entrada
    arquivo = ArquivoDBK.ler(config.arquivo_entrada)
    logger.info("Arquivo de entrada: %s (%d linhas)", config.arquivo_entrada.name, len(arquivo.linhas))

    erro_exercicio = verificar_exercicio(arquivo)
    if erro_exercicio:
        logger.error('Nada foi inserido. %s', erro_exercicio)
        raise SystemExit(1)

    # 2. Ler o JSON do cliente
    dados = json.loads(config.arquivo_dados.read_text(encoding='utf-8'))
    logger.info("Dados do cliente: %s", config.arquivo_dados.name)

    chaves_das_fichas = {ficha.CHAVE_JSON for ficha in FICHAS}
    for chave in sorted(set(dados) - chaves_das_fichas - CHAVES_JSON_CONHECIDAS):
        logger.warning("A chave '%s' do JSON não é de nenhuma ficha e foi ignorada.", chave)

    # 3. Validar todas as fichas antes de gravar qualquer coisa
    validados = []                      # (ficha, itens, dados_validados) das fichas presentes no JSON
    erros = []
    for ficha in FICHAS:
        itens = dados.get(ficha.CHAVE_JSON, [])
        if not itens:
            continue
        logger.info("%s: %d item(ns) a inserir", ficha.NOME, len(itens))
        dados_validados, erros_ficha = ficha.validar(itens)
        validados.append((ficha, itens, dados_validados))
        erros.extend(f"{ficha.NOME} > {erro}" for erro in erros_ficha)

    if erros:
        logger.error('Nada foi inserido. %d erro(s) no JSON.', len(erros))
        for erro in erros:
            logger.error("  - %s", erro)
        raise SystemExit(1)

    if not validados:
        logger.warning("O JSON não tem itens de nenhuma ficha; o arquivo será gravado sem alterações.")

    # 4. Inserir e gravar
    for ficha, itens, dados_validados in validados:
        ficha.inserir(arquivo, itens, dados_validados)

    arquivo.gravar(config.arquivo_saida)
    logger.info('Arquivo gravado: %s', config.arquivo_saida.name)

if __name__ == '__main__':
    main()
