"""
Ficha Dependentes (registro 25).

Cada item do JSON é um dependente:

    {"tipo": "21", "nome": "FILHO X", "cpf": "777.888.999-41", "data_nascimento": "2015-05-10",
     "mora_com_titular": true, "email": "x@y.com", "ddd": "11", "celular": "912345678",
     "raca_cor": "parda"}

    - obrigatórios: tipo, nome, cpf, data_nascimento;
    - opcionais: mora_com_titular (false se ausente), email, ddd e celular (os dois juntos), raca_cor
      ("amarela", "branca", "indigena", "parda" ou "preta").

Busca pelo CPF, só nas linhas do DBK de entrada (docs/adr/0024):
    nenhum           -> dependente novo, com a próxima chave, depois do último dependente;
    1 no DBK         -> campo em branco no DBK recebe o do JSON (a importação da declaração anterior
                        traz o dependente sem o tipo); campo preenchido e diferente fica e gera aviso;
    2 ou mais        -> revisão.
CPF de alimentando do DBK também vai para revisão (o programa acusa erro).

Origem:
    - Regras da tela: leiautes/irpf2026/tabela_dependentes.py (classe Dependente do IRPF 2026, lida com
      javap): tipo, nome, CPF e data obrigatórios (erro); CPF com dígito, diferente do titular e sem
      repetir; limites de idade por tipo; e-mail com o formato do programa; DDD de 2 dígitos e celular
      de 9, um exigindo o outro.
    - Confirmado em DBK gravado pelo programa em 18/11/2026 (tests/dados/dependentes_programa.DBK, 4
      dependentes digitados na ordem 31, 21, 11, 22): o programa mantém a ordem em que foram digitados
      e numera a chave em sequência (1 a 4); "mora com o titular" gravado como 1 ou 0; raça/cor 0 sem
      resposta; e-mail em maiúsculas.
    - Importação da declaração anterior: traz o dependente com a chave, nome, nascimento e CPF e sem o
      tipo (DBK importado do IRPF 2025 em 18/11/2026, tests/dados/pagamentos_importados.DBK).
    - Nome: regra do ValidadorNomeIRPF (leiautes/irpf2026/nome_pessoa.py); só letras e espaços.
    - DDD e celular: a tela só os mostra se o titular mora no Brasil ou se o dependente não mora com
      ele (PainelDependentesDetalhe.configuraIndicadorTitularExterior). Com titular no exterior e
      "mora com o titular", o programa descarta os dois na restauração (roteiro manual de 18/11/2026).
      O bot não lê a residência do titular; grava o que veio no JSON.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from irpf_bot_2027.comum.conversoes import data_do_dbk, so_digitos
from irpf_bot_2027.comum.documentos import cpf_valido
from irpf_bot_2027.comum.texto import caracteres_fora_do_latin1, normalizar_texto
from irpf_bot_2027.dbk import ArquivoDBK
from irpf_bot_2027.leiautes.atual import ANO_CALENDARIO, Registro25, Registro35, erro_nome_pessoa
from irpf_bot_2027.leiautes.atual import tabela_dependentes as tabela

logger = logging.getLogger(__name__)

NOME = "Dependentes"
CHAVE_JSON = "dependentes"

# JSON -> campo do Registro25
CAMPOS_JSON = {
    "tipo": "CODIGO", "nome": "NOME", "cpf": "CPF_DEPENDENTE", "data_nascimento": "DATA_NASCIMENTO",
    "mora_com_titular": "MORA_COM_TITULAR", "email": "EMAIL", "ddd": "DDD_CELULAR", "celular": "CELULAR",
    "raca_cor": "RACA_COR",
}
OBRIGATORIOS = ("tipo", "nome", "cpf", "data_nascimento")
# Dependente$10: formato de e-mail aceito pelo programa.
EMAIL = re.compile(r"^[_A-Za-z0-9-\+]+(\.[_A-Za-z0-9-]+)*@[A-Za-z0-9-]+(\.[A-Za-z0-9]+)*(\.[A-Za-z]{2,})$")

# --- validação ---

def _informado(item: dict, chave: str) -> bool:
    return item.get(chave) is not None and str(item[chave]).strip() != ""

def validar_item(item: dict, cpf_declarante: str | None) -> tuple[dict, list[str]]:
    """Campos do Registro25 já convertidos e os erros. As mensagens não repetem os dados."""
    campos, erros = {}, []
    if not isinstance(item, dict):
        return campos, ["esperado um objeto com os campos do dependente"]
    for chave in sorted(set(item) - set(CAMPOS_JSON)):
        erros.append(f"campo desconhecido '{chave}'")
    for chave in OBRIGATORIOS:
        if not _informado(item, chave):
            erros.append(f"campo obrigatório '{chave}' não informado")

    tipo = str(item.get("tipo", "")).strip()
    if tipo and not tabela.tipo_existe(tipo):
        erros.append(f"'tipo': esperado um dos códigos da ficha ({', '.join(tabela.TIPOS)})")
    elif tipo:
        campos["CODIGO"] = tipo

    if _informado(item, "nome"):
        nome = normalizar_texto(str(item["nome"]))
        fora = caracteres_fora_do_latin1(nome.upper())
        if fora:
            erros.append(f"'nome': caractere(s) não aceito(s) pelo programa: {', '.join(repr(c) for c in fora)}")
        elif len(nome) > Registro25.NOME.tamanho:
            erros.append(f"'nome': tem {len(nome)} caracteres; o máximo é {Registro25.NOME.tamanho}")
        elif erro_nome_pessoa(nome):
            erros.append(f"'nome': {erro_nome_pessoa(nome)}")
        else:
            campos["NOME"] = nome

    if _informado(item, "cpf"):
        cpf = so_digitos(item["cpf"])
        if not cpf_valido(cpf):
            erros.append("'cpf': CPF (11 dígitos) inválido")
        elif cpf == cpf_declarante:
            erros.append("'cpf': o dependente não pode ser o próprio declarante")
        else:
            campos["CPF_DEPENDENTE"] = cpf

    if _informado(item, "data_nascimento"):
        try:
            nascimento = date.fromisoformat(str(item["data_nascimento"]))
        except ValueError:
            erros.append("'data_nascimento': esperada data no formato \"AAAA-MM-DD\"")
        else:
            limite = tabela.NASCIDO_A_PARTIR_DE.get(tipo)
            if nascimento.year > int(ANO_CALENDARIO):
                erros.append(f"'data_nascimento': posterior ao ano-calendário {ANO_CALENDARIO}")
            elif limite and nascimento < date(limite, 1, 1):
                erros.append(f"'data_nascimento': o tipo {tipo} exige nascimento a partir de 01/01/{limite}")
            else:
                campos["DATA_NASCIMENTO"] = nascimento.strftime("%d%m%Y")

    if "mora_com_titular" in item:
        mora = item["mora_com_titular"]
        if not isinstance(mora, bool):
            erros.append("'mora_com_titular': esperado true ou false")
        else:
            campos["MORA_COM_TITULAR"] = "1" if mora else "0"

    if _informado(item, "email"):
        email = str(item["email"]).strip()
        if not EMAIL.match(email) or len(email) > Registro25.EMAIL.tamanho:
            erros.append("'email': formato inválido (ex.: \"nome@dominio.com\")")
        else:
            campos["EMAIL"] = email
    ddd, celular = so_digitos(item.get("ddd") or ""), so_digitos(item.get("celular") or "")
    if ddd or celular:
        if len(ddd) != 2 or len(celular) != 9:
            erros.append("'ddd' e 'celular': informe os dois, com 2 e 9 dígitos")
        else:
            campos["DDD_CELULAR"], campos["CELULAR"] = ddd, celular

    if _informado(item, "raca_cor"):
        raca = normalizar_texto(str(item["raca_cor"])).lower().replace("í", "i")
        if raca not in tabela.RACA_COR:
            erros.append(f"'raca_cor': esperado um de {', '.join(repr(r) for r in tabela.RACA_COR)}")
        else:
            campos["RACA_COR"] = tabela.RACA_COR[raca]
    return campos, erros

def validar(itens: list[dict], cpf_declarante: str | None = None) -> tuple[list[dict], list[str]]:
    campos_por_item, erros = [], []
    for numero, item in enumerate(itens, start=1):
        campos, erros_item = validar_item(item, cpf_declarante)
        campos_por_item.append(campos)
        erros.extend(f"dependente {numero}: {erro}" for erro in erros_item)
    repetidos = Counter(c["CPF_DEPENDENTE"] for c in campos_por_item if "CPF_DEPENDENTE" in c)
    for numero, campos in enumerate(campos_por_item, start=1):
        if repetidos[campos.get("CPF_DEPENDENTE")] > 1:
            erros.append(f"dependente {numero}: 'cpf': o mesmo CPF aparece em outro dependente do JSON")
    return campos_por_item, erros

# --- gravação ---

def montar_linha(campos: dict, cpf: str, chave: int) -> str:
    linha = Registro25.linha_vazia()
    linha = Registro25.TIPO_REGISTRO.gravar(linha, 25)
    linha = Registro25.CPF.gravar(linha, cpf)
    linha = Registro25.CHAVE.gravar(linha, chave)
    linha = Registro25.MORA_COM_TITULAR.gravar(linha, "0")     # o programa grava 0 quando não marcado
    for nome, valor in campos.items():
        linha = getattr(Registro25, nome).gravar(linha, valor)
    return Registro25.gravar_cod_controle(linha)        # sempre por último

def _em_branco(campo, linha: str) -> bool:
    valor = campo.ler(linha).strip()
    return not valor or (campo.tipo == "N" and int(valor) == 0)

def atualizar_linha(linha: str, campos: dict) -> tuple[str, list[str]]:
    """Dependente encontrado: campo em branco recebe o valor do JSON; preenchido e diferente fica e
    entra na lista devolvida (nomes dos campos do JSON, sem os valores)."""
    diferentes = []
    for chave_json, nome in CAMPOS_JSON.items():
        if nome not in campos:
            continue
        campo = getattr(Registro25, nome)
        if _em_branco(campo, linha):
            linha = campo.gravar(linha, campos[nome])
        elif campo.ler(linha) != campo.formatar(campos[nome]):
            diferentes.append(chave_json)
    return Registro25.gravar_cod_controle(linha), diferentes

@dataclass
class Resultado:
    """Dependentes do JSON pelo número (a partir de 1); do DBK pela ordem na ficha (a partir de 1)."""
    encontrados: list[int] = field(default_factory=list)        # já no DBK; campos em branco preenchidos
    novos: list[int] = field(default_factory=list)
    revisao: list[int] = field(default_factory=list)
    diferentes: list[int] = field(default_factory=list)         # encontrados com campo diferente do JSON
    dbk_nao_informados: list[int] = field(default_factory=list)

def inserir(arquivo: ArquivoDBK, itens: list[dict], campos_por_item: list[dict]) -> Resultado:
    resultado = Resultado()
    cpf = arquivo.cpf_declarante
    entrada = arquivo.indices(Registro25.TIPO)             # os novos entram depois: posições não mudam
    alimentandos = {Registro35.CPF_ALIMENTANDO.ler(l).strip() for l in arquivo.linhas_do_tipo(Registro35.TIPO)}
    usados = set()

    for numero, campos in enumerate(campos_por_item, start=1):
        descricao = f"Dependente {numero}"
        cpf_dependente = campos["CPF_DEPENDENTE"]
        if cpf_dependente in alimentandos:
            logger.warning("%s: o CPF é de um alimentando do DBK; não foi gravado (revisão).", descricao)
            resultado.revisao.append(numero)
            continue
        encontrados = [(ordem, posicao) for ordem, posicao in enumerate(entrada, start=1)
                       if Registro25.CPF_DEPENDENTE.ler(arquivo.linhas[posicao]).strip() == cpf_dependente]
        if len(encontrados) > 1:
            logger.warning("%s: %d dependentes no DBK com o mesmo CPF; não foi gravado (revisão).",
                           descricao, len(encontrados))
            resultado.revisao.append(numero)
            usados.update(ordem for ordem, _ in encontrados)
            continue
        if encontrados:
            ordem, posicao = encontrados[0]
            usados.add(ordem)
            nova, diferentes = atualizar_linha(arquivo.linhas[posicao], campos)
            arquivo.substituir(posicao, nova)
            if diferentes:
                logger.warning("%s: no DBK, campo(s) diferente(s) do JSON mantido(s): %s.", descricao,
                               ", ".join(diferentes))
                resultado.diferentes.append(numero)
            logger.info("%s encontrado no DBK (linha %d)", descricao, posicao + 1)
            resultado.encontrados.append(numero)
            continue

        chaves = [int(Registro25.CHAVE.ler(l)) for l in arquivo.linhas_do_tipo(Registro25.TIPO)]
        posicao = arquivo.inserir(Registro25.TIPO, montar_linha(campos, cpf, max(chaves, default=0) + 1))
        logger.info("%s inserido na linha %d", descricao, posicao + 1)
        resultado.novos.append(numero)

    resultado.dbk_nao_informados = [ordem for ordem in range(1, len(entrada) + 1) if ordem not in usados]
    return resultado

def exportar(arquivo: ArquivoDBK) -> list[dict]:
    """Dependentes do DBK no formato do JSON de entrada, com a chave em "dbk" (docs/adr/0026).
    Campo em branco no DBK (ex.: o tipo do dependente importado) não sai no JSON."""
    racas = {codigo: nome for nome, codigo in tabela.RACA_COR.items()}
    itens = []
    for linha in arquivo.linhas_do_tipo(Registro25.TIPO):
        ler = lambda nome: getattr(Registro25, nome).ler(linha).strip()
        item = {"tipo": ler("CODIGO"), "nome": ler("NOME"), "cpf": ler("CPF_DEPENDENTE"),
                "data_nascimento": data_do_dbk(ler("DATA_NASCIMENTO")),
                "mora_com_titular": {"1": True, "0": False}.get(ler("MORA_COM_TITULAR")),
                "email": ler("EMAIL").lower(), "ddd": ler("DDD_CELULAR"), "celular": ler("CELULAR"),
                "raca_cor": racas.get(int(ler("RACA_COR") or 0))}
        item = {chave: valor for chave, valor in item.items() if valor not in (None, "")}
        item["dbk"] = {"chave": int(ler("CHAVE"))}
        itens.append(item)
    return itens

def relatorio(resultado: Resultado) -> list[tuple[int, str]]:
    def numeros(lista: list[int]) -> str:
        return ", ".join(map(str, lista))

    linhas = [(logging.INFO, f"{NOME}: {len(resultado.encontrados)} encontrado(s), {len(resultado.novos)} novo(s), "
                             f"{len(resultado.revisao)} para revisão")]
    if resultado.encontrados:
        linhas.append((logging.INFO, "  encontrados no DBK, campos em branco preenchidos (dependentes do JSON): "
                                     f"{numeros(resultado.encontrados)}"))
    if resultado.novos:
        linhas.append((logging.INFO, f"  lançados como novos (dependentes do JSON): {numeros(resultado.novos)}"))
    if resultado.diferentes:
        linhas.append((logging.WARNING, "  CONFERIR, campos do DBK diferentes do JSON, mantidos (dependentes do "
                                        f"JSON): {numeros(resultado.diferentes)}"))
    if resultado.revisao:
        linhas.append((logging.WARNING, f"  REVISÃO, não gravados (dependentes do JSON): {numeros(resultado.revisao)}"))
    if resultado.dbk_nao_informados:
        linhas.append((logging.WARNING, "  REVISÃO, dependentes do DBK que não vieram no JSON (itens da ficha): "
                                        f"{numeros(resultado.dbk_nao_informados)}"))
    return linhas
