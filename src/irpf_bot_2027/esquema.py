"""
JSON Schema do JSON de entrada do bot, gerado das mesmas tabelas e constantes que a validação usa
(docs/adr/0028). É o formato que a etapa de IA deve devolver (docs/ia/prompt.md).

Uso (no WSL):  uv run irpf-bot-2027-esquema docs/ia
               (grava esquema_entrada.json, o que o bot recebe, e esquema_ia.json, a saída da IA, com
               os dados anonimizados)

O esquema descreve a forma (campos, tipos, códigos aceitos, formatos); as regras que dependem da
combinação de campos (quais blocos cada grupo/código de bem aceita, quais campos cada código de
pagamento exige) estão nas descrições e continuam conferidas pelo bot, que devolve mensagens sem dados
do cliente, próprias para voltar à IA para correção. tests/test_esquema.py confere que o arquivo em
docs/ia/ está em dia com o código.
"""

import argparse
import json
from pathlib import Path

from irpf_bot_2027.fichas.alimentandos import validacao as alimentandos
from irpf_bot_2027.fichas.bens.entrada import CAMPOS_OBRIGATORIOS as OBRIGATORIOS_BEM
from irpf_bot_2027.fichas.bens.entrada import CAMPOS_SIMPLES, MAPA_BLOCOS
from irpf_bot_2027.fichas.bens.exportacao import SIM_NAO
from irpf_bot_2027.fichas.dependentes import ficha as dependentes
from irpf_bot_2027.fichas.pagamentos import validacao as pagamentos
from irpf_bot_2027.fichas.rendimentos_pj import ficha as rendimentos_pj
from irpf_bot_2027.leiautes.atual import ANO_CALENDARIO, EXERCICIO, Registro27
from irpf_bot_2027.leiautes.atual import tabela_dependentes, tabela_pagamentos
from irpf_bot_2027.leiautes.irpf2026.tabela_bens import GRUPOS

VALOR = {"type": "string", "pattern": r"^\d+(\.\d{1,2})?$", "description": 'reais com ponto decimal, ex.: "1234.56"'}
VALOR_COM_SINAL = {**VALOR, "pattern": r"^-?\d+(\.\d{1,2})?$", "description": 'reais; prejuízo com "-", ex.: "-250.00"'}
DATA = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": '"AAAA-MM-DD"'}
CPF = {"type": "string", "pattern": r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$", "description": "CPF, com ou sem pontuação"}
CPF_CNPJ = {"type": "string", "pattern": r"^(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})$",
            "description": "CPF ou CNPJ, com ou sem pontuação"}
ORIGEM = {
    "type": "array", "minItems": 1,
    "description": "documentos de onde o item saiu (para o contador conferir); não vai para o DBK",
    "items": {"type": "object", "additionalProperties": False, "required": ["documento"],
              "properties": {"documento": {"type": "string", "minLength": 1},
                             "pagina": {"type": "integer", "minimum": 1}}},
}


def texto(tamanho: int, descricao: str = "") -> dict:
    esquema = {"type": "string", "minLength": 1, "maxLength": tamanho}
    return {**esquema, "description": descricao} if descricao else esquema


def referencia(chave: str, descricao: str) -> dict:
    return {"type": "object", "additionalProperties": False, "required": [chave],
            "properties": {chave: {"type": "integer", "minimum": 1}},
            "description": f"item do DBK exportado que este atualiza ({descricao}); omitir se for novo"}


def lista(item: dict) -> dict:
    return {"type": "array", "items": item}


def objeto(propriedades: dict, obrigatorios=(), descricao: str = "") -> dict:
    esquema = {"type": "object", "additionalProperties": False, "properties": propriedades}
    if obrigatorios:
        esquema["required"] = list(obrigatorios)
    if descricao:
        esquema["description"] = descricao
    return esquema


def com_controle(propriedades: dict, chave_ref: str, descricao_ref: str, campos_da_validacao=None) -> dict:
    """Acrescenta "dbk" e "origem"; com campos_da_validacao, confere que o esquema tem exatamente os campos
    que a validação da ficha aceita (um campo novo na validação sem o esquema faz a geração falhar)."""
    if campos_da_validacao is not None and set(propriedades) != set(campos_da_validacao):
        raise AssertionError(f"esquema fora de dia: {sorted(set(propriedades) ^ set(campos_da_validacao))}")
    return {**propriedades, "dbk": referencia(chave_ref, descricao_ref), "origem": ORIGEM}


# --- fichas ---

def esquema_rendimentos_pj() -> dict:
    campos = {"cnpj_cpf": CPF_CNPJ, "nome": texto(60, "nome da fonte pagadora")}
    campos.update({chave: VALOR for chave in rendimentos_pj.VALORES})
    return objeto(com_controle(campos, "item", "ordem da fonte na ficha", rendimentos_pj.CAMPOS_JSON),
                  rendimentos_pj.CAMPOS_JSON,
                  "um informe de rendimentos (fonte pagadora PJ do titular); todos os valores obrigatórios, "
                  '"0.00" quando não houver')


def esquema_dependentes() -> dict:
    campos = {
        "tipo": {"type": "string", "enum": list(tabela_dependentes.TIPOS),
                 "description": "; ".join(f"{c} {n}" for c, n in tabela_dependentes.TIPOS.items())},
        "nome": texto(60, "só letras e espaços (sem hífen, apóstrofo ou números)"),
        "cpf": CPF, "data_nascimento": DATA, "mora_com_titular": {"type": "boolean"},
        "email": {"type": "string"}, "ddd": {"type": "string", "pattern": r"^\d{2}$"},
        "celular": {"type": "string", "pattern": r"^\d{4,5}-?\d{4}$"},
        "raca_cor": {"type": "string", "enum": list(tabela_dependentes.RACA_COR)},
    }
    return objeto(com_controle(campos, "chave", "chave do dependente", dependentes.CAMPOS_JSON),
                  dependentes.OBRIGATORIOS)


def esquema_alimentandos() -> dict:
    blocos = {}
    for nome_bloco, mapa in alimentandos.BLOCOS.items():
        propriedades = {chave: DATA if chave == "data" else
                        {"type": "string", "enum": sorted(alimentandos.UFS)} if chave == "uf" else
                        {"type": "string"} for chave in mapa}
        blocos[nome_bloco] = objeto(propriedades, ["data"])
    campos = {"nome": texto(60, "só letras e espaços"), "cpf": CPF, "data_nascimento": DATA,
              "residente": {"type": "string", "enum": list(alimentandos.RESIDENCIA)},
              "alimentando_de": {**CPF, "description": "CPF do titular ou de um dependente"}, **blocos}
    return objeto(com_controle(campos, "chave", "chave do alimentando", alimentandos.CAMPOS_JSON),
                  alimentandos.OBRIGATORIOS,
                  "informe decisao_judicial, escritura_publica ou os dois (tipo de processo)")


def esquema_pagamentos() -> dict:
    t = tabela_pagamentos
    def codigos(conjunto) -> str:
        return ", ".join(sorted(conjunto))
    regras = [
        f"tipo (T titular, D dependente, A alimentando) obrigatório nos códigos {codigos(t.TIPOS)}; "
        f"36, 37 e 99 só T ou D",
        f"CPF obrigatório: {codigos(t.CPF_OBRIGATORIO)}; CNPJ obrigatório: {codigos(t.CNPJ_OBRIGATORIO)}; "
        f"CPF ou CNPJ: {codigos(t.NI_OBRIGATORIO)}; opcional: {codigos(t.NI_OPCIONAL)}",
        f"exterior ({codigos(t.EXTERIOR)}): sem cnpj_cpf, com pais",
        f"pensão ({codigos(t.PENSAO)}): sem tipo, cnpj_cpf e nome; cpf_dependente_alimentando = o alimentando",
        f"parcela_nao_dedutivel só em {codigos(t.COM_PARCELA_NAO_DEDUTIVEL)}",
        f"descricao obrigatória em {codigos(t.DESCRICAO_OBRIGATORIA)}",
        "um item por beneficiário, código, tipo e dependente/alimentando: somar os recibos do ano",
    ]
    campos = {
        "codigo": {"type": "string", "enum": list(t.CODIGOS),
                   "description": "; ".join(f"{c} {n}" for c, n in t.CODIGOS.items())},
        "tipo": {"type": "string", "enum": ["T", "D", "A"]},
        "cpf_dependente_alimentando": CPF, "cnpj_cpf": CPF_CNPJ, "nome": texto(60),
        "valor_pago": VALOR, "parcela_nao_dedutivel": VALOR, "descricao": texto(512),
        "pais": {"type": "string", "pattern": r"^\d{1,3}$", "description": "código do país (tabela do programa)"},
    }
    return objeto(com_controle(campos, "item", "ordem do pagamento na ficha", pagamentos.CAMPOS_JSON),
                  ["codigo", "valor_pago"],
                  ". ".join(regras))


def _campo_de_bem(nome: str) -> dict:
    if nome in SIM_NAO:
        return {"type": "boolean"}
    if nome == "AF_RENDIMENTO":
        return VALOR_COM_SINAL
    if nome in ("VALOR_ANTERIOR", "VALOR_ATUAL", "AF_IMPOSTO", "LD_RECEBIDO", "LD_IMPOSTO"):
        return VALOR
    if nome == "AREA":
        return {"type": "string", "pattern": r"^\d+(\.\d)?$", "description": 'uma casa decimal, ex.: "75.5"'}
    if nome == "UNIDADE_AREA":
        return {"type": "string", "enum": ["m2", "ha"]}
    if nome == "DATA_AQUISICAO":
        return DATA
    if nome == "TITULAR_DEPENDENTE":
        return {"type": "string", "enum": ["T", "D"]}
    if nome == "PAIS":
        return {"type": "string", "pattern": r"^\d{1,3}$", "description": 'código do país, "105" = Brasil'}
    if nome in ("CPF_DONO",):
        return CPF
    if nome in ("CNPJ_CPF",):
        return CPF_CNPJ
    campo = getattr(Registro27, nome)
    return {"type": "string", "maxLength": campo.tamanho} if campo.tipo != "N" else {"type": "string"}


def esquema_bens() -> dict:
    campos = {chave: _campo_de_bem(nome) for chave, nome in CAMPOS_SIMPLES.items()}
    campos["grupo"] = {"type": "string", "enum": list(GRUPOS),
                       "description": "; ".join(f"{g} {d['nome']}" for g, d in GRUPOS.items())}
    campos["codigo"] = {"type": "string", "pattern": r"^\d{2}$", "description": "códigos por grupo: " + " | ".join(
        f"{g}: " + ", ".join(f"{c} {n}" for c, n in d["codigos"].items()) for g, d in GRUPOS.items())}
    for bloco, mapa in MAPA_BLOCOS.items():
        campos[bloco] = objeto({chave: _campo_de_bem(nome) for chave, nome in mapa.items()})
    campos["situacao_anterior"] = {**VALOR, "description": f"situação em 31/12/{int(ANO_CALENDARIO) - 1}; "
                                   "num bem do DBK, a mesma do DBK"}
    campos["situacao_atual"] = {**VALOR, "description": f"situação em 31/12/{ANO_CALENDARIO}"}
    return objeto(com_controle(campos, "chave", "chave do bem", [*CAMPOS_SIMPLES, *MAPA_BLOCOS]), OBRIGATORIOS_BEM,
                  "os blocos aceitos dependem do grupo/código/país (o bot confere e diz o que falta ou sobra)")


ANONIMIZAVEIS = {CPF["pattern"], CPF_CNPJ["pattern"], r"^\d{2}$", r"^\d{4,5}-?\d{4}$"}


def _anonimizavel(esquema):
    """Versão para a saída da IA: CPF, CPF/CNPJ, telefone e os identificadores dos bens (os textos sem
    tamanho mínimo) aceitam o código da anonimização (ex.: "CPF_0007") no lugar do dado real."""
    if isinstance(esquema, dict):
        esquema = {chave: _anonimizavel(valor) for chave, valor in esquema.items()}
        if esquema.get("pattern") in ANONIMIZAVEIS:
            del esquema["pattern"]
            esquema["description"] = (esquema.get("description", "") + "; dado real ou código da anonimização").lstrip("; ")
        if esquema.get("type") == "string" and "maxLength" in esquema and "minLength" not in esquema:
            del esquema["maxLength"]
        return esquema
    if isinstance(esquema, list):
        return [_anonimizavel(valor) for valor in esquema]
    return esquema


def gerar(anonimizado: bool = False) -> dict:
    """Esquema do JSON de entrada do bot; com anonimizado=True, o da saída da etapa de IA (docs/ia/)."""
    esquema = _gerar()
    if anonimizado:
        esquema = _anonimizavel(esquema)
        esquema["title"] = esquema["title"].replace("JSON de entrada do irpf-bot", "Saída da etapa de IA")
        esquema["description"] += (" Versão com os dados anonimizados: os campos de pessoa física e os "
                                   "identificadores aceitam o código da anonimização.")
    return esquema


def _gerar() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"JSON de entrada do irpf-bot (IRPF {EXERCICIO}, ano-calendário {ANO_CALENDARIO})",
        "description": "Só o que entra ou muda na declaração; o que não vier continua no DBK como está. "
                       "Gerado por src/irpf_bot_2027/esquema.py: não edite à mão.",
        "type": "object", "additionalProperties": False, "required": ["cpf"],
        "properties": {
            "cpf": {**CPF, "description": "CPF do declarante (o do DBK)"},
            "rendimentos_pj": lista(esquema_rendimentos_pj()),
            "dependentes": lista(esquema_dependentes()),
            "alimentandos": lista(esquema_alimentandos()),
            "pagamentos": lista(esquema_pagamentos()),
            "bens": lista(esquema_bens()),
            "pendencias": lista(objeto({"descricao": {"type": "string", "minLength": 1},
                                        "origem": ORIGEM}, ["descricao"],
                                       "o que a IA não decidiu sozinha, para o contador")),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os JSON Schemas: entrada do bot e saída da IA.")
    parser.add_argument("pasta", type=Path, help="pasta onde gravar (docs/ia)")
    args = parser.parse_args()
    args.pasta.mkdir(parents=True, exist_ok=True)
    for nome, anonimizado in (("esquema_entrada.json", False), ("esquema_ia.json", True)):
        (args.pasta / nome).write_text(json.dumps(gerar(anonimizado), ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")


if __name__ == "__main__":
    main()
