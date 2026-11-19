"""
Pseudonimização do JSON do DBK antes de ele ir para a IA, e o caminho de volta (docs/adr/0029).

Os documentos do cliente chegam com os dados sensíveis **apagados** pelo software do escritório (não
trocados por códigos). O JSON do DBK é pseudonimizado aqui: cada dado de pessoa física e cada
identificador que leva ao dono vira um código estável dentro da execução (ex.: "CPF_0003"), guardado
numa tabela que nunca sai da máquina. A IA copia os códigos para os itens que casam com o DBK, e a
volta troca os códigos pelos dados reais antes de o JSON chegar ao bot.

    pessoas físicas:   CPF (titular, dependentes, alimentandos, beneficiários e fontes PF), nomes de
                       dependentes, alimentandos e beneficiários PF, e-mail, DDD, celular
    identificadores:   conta bancária, Renavam e registros de aeronave/embarcação, endereço, CEP,
                       IPTU, CIB, CEI/CNO e matrícula do imóvel, número do processo judicial
    texto livre:       sequências de 6 ou mais dígitos na discriminação e na descrição (contas,
                       CPFs, CNPJs, matrículas escritos no texto)
    ficam abertos:     CNPJ (pessoa jurídica), nome de empresa, valores, códigos da tabela, datas

O mesmo dado (normalizado: só dígitos nos números, maiúsculas nos textos) recebe sempre o mesmo código.
"""

import copy
import re
from dataclasses import dataclass, field

# chave do JSON -> tipo do código (para chaves que são sempre sensíveis, em qualquer ficha ou bloco)
SEMPRE = {
    "cpf": "CPF", "cpf_dependente_alimentando": "CPF", "alimentando_de": "CPF",
    "email": "EMAIL", "ddd": "DDD", "celular": "CELULAR",
    "renavam": "REGISTRO", "registro_aeronave": "REGISTRO", "registro_embarcacao": "REGISTRO",
    "logradouro": "ENDERECO", "numero": "ENDERECO", "complemento": "ENDERECO", "cep": "CEP",
    "iptu": "IPTU", "cib": "CIB", "cei_cno": "CEI", "matricula": "MATRICULA", "processo": "PROCESSO",
}
NUMEROS = {"CPF", "DDD", "CELULAR", "CEP", "CONTA"}           # normalizados para só dígitos
FICHAS_COM_NOME_DE_PESSOA = {"dependentes", "alimentandos"}
TEXTO_LIVRE = {"discriminacao", "descricao"}
NUMERO_NO_TEXTO = re.compile(r"\d[\d.\-/ ]{4,}\d")
CODIGO = re.compile(r"\b(CPF|NOME|EMAIL|DDD|CELULAR|REGISTRO|ENDERECO|CEP|IPTU|CIB|CEI|MATRICULA|PROCESSO|"
                    r"CONTA|NUM)_\d{4}\b")


def _digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


@dataclass
class Tabela:
    """Código <-> dado real, só em memória (ou num arquivo local, se o chamador quiser guardar)."""
    reais: dict[str, str] = field(default_factory=dict)          # código -> valor real (como estava no DBK)
    codigos: dict[tuple[str, str], str] = field(default_factory=dict)   # (tipo, valor normalizado) -> código
    contagem: dict[str, int] = field(default_factory=dict)

    def codigo(self, tipo: str, valor: str) -> str:
        normalizado = _digitos(valor) if tipo in NUMEROS else " ".join(valor.upper().split())
        chave = (tipo, normalizado)
        if chave not in self.codigos:
            self.contagem[tipo] = self.contagem.get(tipo, 0) + 1
            codigo = f"{tipo}_{self.contagem[tipo]:04d}"
            self.codigos[chave] = codigo
            self.reais[codigo] = valor
        return self.codigos[chave]


def _eh_cpf(valor) -> bool:
    return isinstance(valor, str) and len(_digitos(valor)) == 11


def _mascarar_texto(texto: str, tabela: Tabela) -> str:
    return NUMERO_NO_TEXTO.sub(lambda m: tabela.codigo("NUM", m.group(0)), texto)


def _pseudonimizar_item(item: dict, ficha: str, tabela: Tabela) -> dict:
    pessoa_fisica = _eh_cpf(item.get("cnpj_cpf"))              # beneficiário ou fonte pessoa física
    saida = {}
    for chave, valor in item.items():
        if isinstance(valor, dict) and chave != "dbk":
            saida[chave] = _pseudonimizar_item(valor, ficha, tabela) if chave != "conta" else {
                k: (tabela.codigo("CONTA", v) if k == "conta" and isinstance(v, str) and v else v)
                for k, v in valor.items()}
            continue
        if not isinstance(valor, str) or not valor:
            saida[chave] = valor
        elif chave in SEMPRE:
            saida[chave] = tabela.codigo(SEMPRE[chave], valor)
        elif chave == "cnpj_cpf" and pessoa_fisica:
            saida[chave] = tabela.codigo("CPF", valor)
        elif chave == "nome" and (ficha in FICHAS_COM_NOME_DE_PESSOA or pessoa_fisica):
            saida[chave] = tabela.codigo("NOME", valor)
        elif chave in TEXTO_LIVRE:
            saida[chave] = _mascarar_texto(valor, tabela)
        else:
            saida[chave] = valor
    return saida


def pseudonimizar(dados: dict) -> tuple[dict, Tabela]:
    """JSON do DBK (formato da exportação) -> (JSON com códigos, tabela para desfazer)."""
    tabela = Tabela()
    saida = {}
    for chave, valor in dados.items():
        if chave == "cpf":
            saida[chave] = tabela.codigo("CPF", valor)
        elif isinstance(valor, list):
            saida[chave] = [_pseudonimizar_item(item, chave, tabela) if isinstance(item, dict) else item
                            for item in valor]
        else:
            saida[chave] = copy.deepcopy(valor)
    return saida, tabela


def desfazer(dados, tabela: Tabela) -> tuple[object, list[str]]:
    """Troca os códigos pelos dados reais, em qualquer lugar do JSON (inclusive dentro de textos).
    Devolve o JSON e os códigos que não existem na tabela (a IA inventou ou copiou errado); as mensagens
    citam só o código, que não é dado do cliente."""
    desconhecidos: list[str] = []

    def trocar(texto: str) -> str:
        if texto in tabela.reais:
            return tabela.reais[texto]
        def um(m: re.Match) -> str:
            if m.group(0) in tabela.reais:
                return tabela.reais[m.group(0)]
            desconhecidos.append(m.group(0))
            return m.group(0)
        return CODIGO.sub(um, texto)

    def andar(valor):
        if isinstance(valor, dict):
            return {chave: andar(v) for chave, v in valor.items()}
        if isinstance(valor, list):
            return [andar(v) for v in valor]
        if isinstance(valor, str):
            return trocar(valor)
        return valor

    return andar(dados), sorted(set(desconhecidos))
