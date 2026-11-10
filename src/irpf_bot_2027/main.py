import json
import logging

from irpf_bot_2027.config import ErroConfiguracao, carregar_config
from irpf_bot_2027.config_log import configurar_log
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas import bens
from irpf_bot_2027.leiautes import irpf2026 as leiaute
from irpf_bot_2027.leiautes.irpf2026.cabecalho import CabecalhoIR

logger = logging.getLogger(__name__)

def verificar_exercicio(arquivo: ArquivoDBK) -> str | None:
    """Mensagem de erro se o DBK não for do exercício do leiaute em uso; None se estiver certo."""
    cabecalhos = arquivo.linhas_do_tipo(CabecalhoIR.TIPO)
    if not cabecalhos:
        return 'o arquivo de entrada não tem o cabeçalho "IR"; não parece um DBK do IRPF'

    exercicio = CabecalhoIR.EXERCICIO.ler(cabecalhos[0])
    ano_base = CabecalhoIR.ANO_BASE.ler(cabecalhos[0])
    if (exercicio, ano_base) != (leiaute.EXERCICIO, leiaute.ANO_CALENDARIO):
        return (f'o DBK é do exercício {exercicio} (ano-calendário {ano_base}), mas o bot está usando '
                f'o leiaute do exercício {leiaute.EXERCICIO} (ano-calendário {leiaute.ANO_CALENDARIO})')
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
    lista_bens = dados[bens.CHAVE_JSON]
    logger.info("Dados do cliente: %s (%d bens a inserir)", config.arquivo_dados.name, len(lista_bens))

    # 3. Validar tudo antes de gravar qualquer coisa
    campos_por_bem, erros = bens.validar(lista_bens)
    if erros:
        logger.error('Nada foi inserido. %d erro(s) no JSON.', len(erros))
        for erro in erros:
            logger.error("  - %s", erro)
        raise SystemExit(1)

    # 4. Inserir e gravar
    bens.inserir(arquivo, lista_bens, campos_por_bem)
    arquivo.gravar(config.arquivo_saida)
    logger.info('Arquivo gravado: %s', config.arquivo_saida.name)

if __name__ == '__main__':
    main()
