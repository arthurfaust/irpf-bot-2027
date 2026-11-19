"""
Exporta os alimentandos do DBK para o formato do JSON de entrada (docs/adr/0026).
"""

from irpf_bot_2027.comum.conversoes import data_do_dbk
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas.alimentandos.validacao import BLOCOS, RESIDENCIA, TIPO_PROCESSO
from irpf_bot_2027.leiautes.atual import Registro35

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Alimentandos do DBK no formato do JSON de entrada, com a chave em "dbk" (docs/adr/0026).
    Campo em branco no DBK (ex.: nascimento e processo do importado) não sai no JSON."""
    residencias = {codigo: nome for nome, codigo in RESIDENCIA.items()}
    blocos_do_tipo = {tipo: blocos for blocos, tipo in TIPO_PROCESSO.items()}
    itens = []
    for linha in arquivo.linhas_do_tipo(Registro35.TIPO):
        ler = lambda nome: getattr(Registro35, nome).ler(linha).strip()
        item = {"nome": ler("NOME"), "cpf": ler("CPF_ALIMENTANDO"),
                "data_nascimento": data_do_dbk(ler("DATA_NASCIMENTO")),
                "residente": residencias.get(int(ler("RESIDENCIA") or 0)), "alimentando_de": ler("CPF_VINCULADO")}
        for nome_bloco in blocos_do_tipo.get(ler("TIPO_PROCESSO"), ()):
            bloco = {}
            for chave, nome_campo in BLOCOS[nome_bloco].items():
                valor = ler(nome_campo)
                if chave == "data":
                    valor = data_do_dbk(valor)
                elif nome_campo == "COD_MUNICIPIO" and not valor.strip("0"):
                    valor = None
                if valor:
                    bloco[chave] = valor
            item[nome_bloco] = bloco
        item = {chave: valor for chave, valor in item.items() if valor not in (None, "")}
        item["dbk"] = {"chave": int(ler("CHAVE"))}
        itens.append(item)
    return itens
