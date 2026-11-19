"""
Busca dos pagamentos no DBK (docs/adr/0021 e 0023): a chave do pagamento e o dependente/alimentando
pelo CPF nos registros 25 e 35.
"""

from irpf_bot_2027.comum.texto import normalizar_texto
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import Registro25, Registro26, Registro35

def vinculado_no_dbk(arquivo: ArquivoDBK, tipo: str, cpf: str) -> list[str]:
    """Linhas do dependente (registro 25) ou do alimentando (registro 35) com esse CPF."""
    registro, campo = (Registro25, Registro25.CPF_DEPENDENTE) if tipo == "D" else (Registro35, Registro35.CPF_ALIMENTANDO)
    return [linha for linha in arquivo.linhas_do_tipo(registro.TIPO) if campo.ler(linha).strip() == cpf]

def chave_busca(linha: str) -> tuple:
    """Código, tipo, chave do dependente/alimentando e beneficiário (CPF/CNPJ ou, sem ele, o nome)."""
    ni = Registro26.NI_BENEFICIARIO.ler(linha).strip()
    beneficiario = ni or normalizar_texto(Registro26.NOME_BENEFICIARIO.ler(linha)).upper()
    return (Registro26.CODIGO.ler(linha), Registro26.TIPO_PAGAMENTO.ler(linha).strip(),
            Registro26.CHAVE_DEPENDENTE.ler(linha), beneficiario)

VALORES = ("VALOR_PAGO", "PARCELA_NAO_DEDUTIVEL")

def sem_valores(linha: str) -> bool:
    """Pagamento trazido da declaração anterior: o programa importa tudo menos os valores."""
    return all(int(getattr(Registro26, nome).ler(linha)) == 0 for nome in VALORES)
