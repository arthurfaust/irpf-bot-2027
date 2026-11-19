"""
Exporta os bens do DBK (registro 27) para o formato do JSON de entrada (docs/adr/0026).

Cada bem sai com os campos que a tela mostra para o seu grupo/código/país (regras.campos_aplicaveis)
e que estão preenchidos no DBK, convertidos de volta para o formato do JSON (o inverso de
entrada.CONVERSOES), mais a referência `"dbk": {"chave": N}`.

Lançar de novo os bens exportados num DBK sem bens reproduz as linhas (teste de ida e volta em
tests/test_exportacao.py), desde que as chaves do DBK estejam em sequência a partir de 1.
"""

from irpf_bot_2027.comum.conversoes import data_do_dbk, numero_do_dbk
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.fichas.bens.entrada import CAMPOS_SIMPLES, MAPA_BLOCOS
from irpf_bot_2027.leiautes.atual import Registro27, campos_aplicaveis

GRUPO_CRIPTO = "08"

SIM_NAO = {"USUFRUTO", "AUTOCUSTODIANTE", "REGISTRADO_CARTORIO", "CONTA_PAGAMENTO", "BOLSA"}
UNIDADES = {"0": "m2", "1": "ha"}

# campo do Registro27 -> caminho no JSON (o primeiro de cada campo; CNPJ_CPF da cripto é tratado à parte)
CAMINHOS: dict[str, tuple[str, ...]] = {campo: (chave,) for chave, campo in CAMPOS_SIMPLES.items()}
for _bloco, _mapa in MAPA_BLOCOS.items():
    for _chave, _campo in _mapa.items():
        CAMINHOS.setdefault(_campo, (_bloco, _chave))


def _valor(campo, texto: str):
    """Texto do DBK -> valor do JSON; None quando o campo está em branco ("não informado")."""
    nome = next(n for n, c in Registro27.campos().items() if c is campo)
    if nome in SIM_NAO:
        return {"1": True, "0": False}.get(texto.strip())                # 2 = em branco
    if nome == "UNIDADE_AREA":
        return UNIDADES.get(texto.strip())
    if nome == "DATA_AQUISICAO":
        return data_do_dbk(texto)
    if campo.tipo == "N" and campo.decimais:
        return numero_do_dbk(texto, campo.decimais)
    if nome == "COD_MUNICIPIO":
        return texto if texto.strip("0") else None
    texto = texto.strip()
    return texto or None


def exportar_linha(linha: str) -> dict:
    lido = {nome: getattr(Registro27, nome).ler(linha) for nome in Registro27.campos()}
    grupo, codigo, pais = lido["GRUPO"], lido["CODIGO"], lido["PAIS"]
    aplicaveis = campos_aplicaveis(grupo, codigo, pais, autocustodiante=lido["AUTOCUSTODIANTE"] == "1",
                                   bolsa=lido["BOLSA"] == "1")
    simples, blocos = {}, {}
    for nome in sorted(aplicaveis, key=list(Registro27.campos()).index):
        valor = _valor(getattr(Registro27, nome), lido[nome])
        if valor is None and nome not in ("VALOR_ANTERIOR", "VALOR_ATUAL"):
            continue
        if nome == "CPF_DONO" and lido["TITULAR_DEPENDENTE"] == "T":
            continue                                    # do titular: o programa grava o CPF dele sozinho
        caminho = ("cripto", "cnpj_custodiante") if nome == "CNPJ_CPF" and grupo == GRUPO_CRIPTO else CAMINHOS[nome]
        if len(caminho) == 1:
            simples[caminho[0]] = valor
        else:
            blocos.setdefault(caminho[0], {})[caminho[1]] = valor
    ordem = list(CAMPOS_SIMPLES)
    bem = {chave: simples[chave] for chave in sorted(simples, key=ordem.index)}
    for bloco, mapa in MAPA_BLOCOS.items():
        if bloco in blocos:
            bem[bloco] = {chave: blocos[bloco][chave] for chave in mapa if chave in blocos[bloco]}
    bem["dbk"] = {"chave": int(lido["CHAVE"])}
    return bem


def exportar(arquivo: ArquivoDBK) -> list[dict]:
    return [exportar_linha(linha) for linha in arquivo.linhas_do_tipo(Registro27.TIPO)]
