"""
Exporta os pagamentos do DBK para o formato do JSON de entrada (docs/adr/0026).
"""

from irpf_bot_2027.comum.conversoes import numero_do_dbk
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import Registro25, Registro26, Registro35
from irpf_bot_2027.leiautes.atual import tabela_pagamentos as tabela

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Pagamentos do DBK no formato do JSON de entrada, com a ordem na ficha em "dbk" (docs/adr/0026).
    O dependente/alimentando sai pelo CPF (a chave do DBK é trocada pelo CPF do registro 25 ou 35)."""
    cpfs = {
        "D": {int(Registro25.CHAVE.ler(l)): Registro25.CPF_DEPENDENTE.ler(l).strip()
              for l in arquivo.linhas_do_tipo(Registro25.TIPO)},
        "A": {int(Registro35.CHAVE.ler(l)): Registro35.CPF_ALIMENTANDO.ler(l).strip()
              for l in arquivo.linhas_do_tipo(Registro35.TIPO)},
    }
    itens = []
    for ordem, linha in enumerate(arquivo.linhas_do_tipo(Registro26.TIPO), start=1):
        ler = lambda nome: getattr(Registro26, nome).ler(linha).strip()
        codigo, tipo = ler("CODIGO"), ler("TIPO_PAGAMENTO")
        pensao = codigo in tabela.PENSAO
        item = {"codigo": codigo, "tipo": tipo if codigo in tabela.TIPOS else None,
                "cpf_dependente_alimentando": cpfs.get(tipo, {}).get(int(ler("CHAVE_DEPENDENTE"))),
                "cnpj_cpf": None if pensao or codigo in tabela.EXTERIOR else ler("NI_BENEFICIARIO"),
                "nome": None if pensao else ler("NOME_BENEFICIARIO"),
                "valor_pago": numero_do_dbk(ler("VALOR_PAGO")),
                "parcela_nao_dedutivel": numero_do_dbk(ler("PARCELA_NAO_DEDUTIVEL"))
                if int(ler("PARCELA_NAO_DEDUTIVEL")) and codigo in tabela.COM_PARCELA_NAO_DEDUTIVEL else None,
                "descricao": ler("DESCRICAO"),
                "pais": ler("PAIS") if codigo in tabela.EXTERIOR else None}
        item = {chave: valor for chave, valor in item.items() if valor not in (None, "")}
        item["dbk"] = {"item": ordem}
        itens.append(item)
    return itens
