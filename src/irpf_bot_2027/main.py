import json
import logging

from irpf_bot_2027.config import ErroConfiguracao, carregar_config
from irpf_bot_2027.config_log import configurar_log
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes import irpf2026 as leiaute
from irpf_bot_2027.leiautes.irpf2026.cabecalho import CabecalhoIR
from irpf_bot_2027.leiautes.irpf2026.registro27 import Registro27
from irpf_bot_2027.leiautes.irpf2026.regras import BRASIL, TITULAR_OU_DEPENDENTE, esta_na_tabela
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import nome_codigo
from irpf_bot_2027.validacao import validar_bem

logger = logging.getLogger(__name__)

def proxima_chave(linhas_bens: list[str]) -> int:
    """Maior chave de bem existente + 1 (ou 1, se o DBK não tiver bens)."""
    chaves = [int(Registro27.CHAVE.ler(linha)) for linha in linhas_bens]
    return max(chaves, default=0) + 1

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
    raw_file, new_file, client_data = config.arquivo_entrada, config.arquivo_saida, config.arquivo_dados

    arquivo = ArquivoDBK.ler(raw_file)

    erro_exercicio = verificar_exercicio(arquivo)
    if erro_exercicio:
        logger.error('Nenhum bem foi inserido. %s', erro_exercicio)
        raise SystemExit(1)

    with open(client_data, 'r', encoding='utf-8', newline='') as data:
        dados = json.load(data)

    linhas_bens = arquivo.linhas_do_tipo(Registro27.TIPO)

    logger.info("Arquivo de entrada: %s (%d linhas, %d bens)", raw_file.name, len(arquivo.linhas), len(linhas_bens))
    logger.info("Dados do cliente: %s (%d bens a inserir)", client_data.name, len(dados['bens']))

    chave = proxima_chave(linhas_bens)
    cpf = arquivo.cpf_declarante

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
        lancamento = Registro27.VALOR_ANTERIOR.gravar(lancamento, bem['situacao_anterior'])
        lancamento = Registro27.VALOR_ATUAL.gravar(lancamento, bem['situacao_atual'])
        lancamento = Registro27.USUFRUTO.gravar(lancamento, bem.get('usufruto', False))
        lancamento = Registro27.CHAVE.gravar(lancamento, chave)

        for nome, valor in campos.items():                 # campos dos blocos do JSON, já validados
            lancamento = getattr(Registro27, nome).gravar(lancamento, valor)

        lancamento = Registro27.gravar_cod_controle(lancamento)          # sempre por último

        posicao = arquivo.inserir(Registro27.TIPO, lancamento)
        logger.info("Bem %s/%s (%s) inserido na linha %d com chave %d", bem['grupo'], bem['codigo'], nome_codigo(bem['grupo'], bem['codigo']), posicao + 1, chave)
        logger.info("  campos extras gravados: %s", ", ".join(sorted(campos)) or "nenhum")

        chave += 1

    arquivo.gravar(new_file)
    logger.info('Arquivo gravado: %s', new_file.name)

if __name__ == '__main__':
    main()