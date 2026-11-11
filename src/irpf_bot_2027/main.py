import json
import logging

from irpf_bot_2027.comum.conversoes import so_digitos
from irpf_bot_2027.config import ErroConfiguracao, carregar_config
from irpf_bot_2027.config_log import configurar_log
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import CHAVES_JSON_CONHECIDAS, FICHAS
from irpf_bot_2027.leiautes.atual import verificar_exercicio

logger = logging.getLogger(__name__)

def conferir_cpf(dados: dict, cpf_dbk: str) -> str | None:
    """Mensagem de erro se o "cpf" do JSON faltar ou não for o do declarante do DBK; None se bater.

    Escolha do projeto: o "cpf" é obrigatório, para impedir que os dados de um cliente sejam
    gravados na declaração de outro. As mensagens não repetem os CPFs (dado do cliente).
    """
    if "cpf" not in dados:
        return 'o JSON não tem a chave "cpf" (CPF do declarante, 11 dígitos)'
    cpf = so_digitos(dados["cpf"])
    if len(cpf) != 11:
        return 'o "cpf" do JSON deve ter 11 dígitos (com ou sem pontos e traço)'
    if cpf != cpf_dbk:
        return 'o "cpf" do JSON não é o CPF do declarante do DBK de entrada'
    return None

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

    erro_cpf = conferir_cpf(dados, arquivo.cpf_declarante)
    if erro_cpf:
        logger.error('Nada foi inserido. %s', erro_cpf)
        raise SystemExit(1)

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
        logger.info("%s: %d item(ns) no JSON", ficha.NOME, len(itens))
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

    # 4. Atualizar/inserir e gravar
    resultados = [(ficha, ficha.inserir(arquivo, itens, dados_validados)) for ficha, itens, dados_validados in validados]

    arquivo.gravar(config.arquivo_saida)
    logger.info('Arquivo gravado: %s', config.arquivo_saida.name)

    # 5. Relatório para conferência humana
    logger.info("Relatório da execução:")
    for ficha, resultado in resultados:
        for nivel, texto in ficha.relatorio(resultado):
            logger.log(nivel, texto)

if __name__ == '__main__':
    main()
