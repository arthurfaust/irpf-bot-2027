"""
Provedores de IA da etapa de comparação (docs/adr/0029). O resto da etapa só conhece a classe Provedor;
trocar de provedor é escrever outra subclasse e registrá-la em PROVEDORES.

Contrato:
    with provedor.sessao(documentos) as conversa:     # envia os documentos (e os apaga no fim)
        texto = conversa.iniciar(sistema, pedido, esquema)
        texto = conversa.corrigir(erros)              # mesma conversa: a IA vê o que respondeu antes

`iniciar` e `corrigir` devolvem o texto da resposta (o JSON). Erros do provedor viram ErroIA, com
mensagem sem dados do cliente.
"""

import contextlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TIPOS_DE_DOCUMENTO = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/plain"}


class ErroIA(Exception):
    """Falha da chamada à IA (recusa, resposta cortada, erro da API)."""


class Conversa:
    def iniciar(self, sistema: str, pedido: str, esquema: dict) -> str:
        raise NotImplementedError

    def corrigir(self, erros: str) -> str:
        raise NotImplementedError


class Provedor:
    nome = "base"

    def sessao(self, documentos: list[Path]) -> contextlib.AbstractContextManager[Conversa]:
        raise NotImplementedError


# --- Claude (Anthropic) ---

def esquema_para_a_api(esquema):
    """A saída estruturada da API não aceita restrições de tamanho e numéricas (minLength, maxLength,
    minimum, minItems...); elas são tiradas daqui e conferidas depois, localmente, com o esquema inteiro."""
    retirar = {"$schema", "minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems"}
    if isinstance(esquema, dict):
        return {chave: esquema_para_a_api(valor) for chave, valor in esquema.items() if chave not in retirar}
    if isinstance(esquema, list):
        return [esquema_para_a_api(valor) for valor in esquema]
    return esquema


class ConversaClaude(Conversa):
    def __init__(self, cliente, modelo: str, esforco: str, blocos_dos_documentos: list[dict]):
        self.cliente = cliente
        self.modelo = modelo
        self.esforco = esforco
        self.blocos_dos_documentos = blocos_dos_documentos
        self.sistema = None
        self.esquema = None
        self.mensagens: list[dict] = []

    def _pedir(self) -> str:
        import anthropic
        try:
            with self.cliente.beta.messages.stream(
                model=self.modelo,
                max_tokens=64000,
                system=[{"type": "text", "text": self.sistema, "cache_control": {"type": "ephemeral"}}],
                messages=self.mensagens,
                thinking={"type": "adaptive"},
                output_config={"effort": self.esforco,
                               "format": {"type": "json_schema", "schema": self.esquema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",            # recusa de segurança: o servidor tenta outro modelo
            ) as stream:
                resposta = stream.get_final_message()
        except anthropic.BadRequestError as erro:
            raise ErroIA(f"a API recusou o pedido (400): {erro.message}") from None
        except anthropic.AuthenticationError:
            raise ErroIA("sem credencial da Anthropic: rode `ant auth login` ou defina ANTHROPIC_API_KEY") from None
        except anthropic.RateLimitError:
            raise ErroIA("limite de uso da API atingido; tente de novo mais tarde") from None
        except anthropic.APIStatusError as erro:
            raise ErroIA(f"erro da API ({erro.status_code}); request-id {getattr(erro, 'request_id', None)}") from None
        except anthropic.APIConnectionError:
            raise ErroIA("sem conexão com a API da Anthropic") from None

        uso = resposta.usage
        logger.info("IA: %s, %d tokens de entrada (%d do cache), %d de saída", resposta.model,
                    uso.input_tokens, uso.cache_read_input_tokens or 0, uso.output_tokens)
        if resposta.stop_reason == "refusal":
            categoria = resposta.stop_details.category if resposta.stop_details else None
            raise ErroIA(f"a IA recusou o pedido (categoria: {categoria})")
        if resposta.stop_reason == "max_tokens":
            raise ErroIA("a resposta da IA foi cortada (limite de tokens); divida os documentos em lotes")
        # a conversa guarda a resposta inteira (inclusive os blocos de raciocínio) para a correção
        self.mensagens.append({"role": "assistant", "content": resposta.content})
        return next(bloco.text for bloco in resposta.content if bloco.type == "text")

    def iniciar(self, sistema: str, pedido: str, esquema: dict) -> str:
        self.sistema = sistema
        self.esquema = esquema_para_a_api(esquema)
        self.mensagens = [{"role": "user", "content": [*self.blocos_dos_documentos, {"type": "text", "text": pedido}]}]
        return self._pedir()

    def corrigir(self, erros: str) -> str:
        self.mensagens.append({"role": "user", "content": erros})
        return self._pedir()


class ProvedorClaude(Provedor):
    """Claude pela API da Anthropic. Os documentos vão pela Files API (o pedido com PDFs em base64 tem
    limite de 32 MB) e são apagados no fim da sessão. Credencial: `ant auth login` ou ANTHROPIC_API_KEY."""
    nome = "claude"

    def __init__(self, modelo: str = "claude-opus-5-5", esforco: str = "high"):
        self.modelo = modelo
        self.esforco = esforco

    @contextlib.contextmanager
    def sessao(self, documentos: list[Path]):
        try:
            import anthropic
        except ImportError:
            raise ErroIA("instale o extra da etapa de IA: uv sync --extra ia") from None
        cliente = anthropic.Anthropic()
        enviados = []
        try:
            blocos = []
            for caminho in documentos:
                tipo = TIPOS_DE_DOCUMENTO[caminho.suffix.lower()]
                # expira sozinho em 1 hora, mesmo que a exclusão no fim da sessão falhe
                arquivo = cliente.files.upload(file=(caminho.name, caminho.read_bytes(), tipo),
                                               expires_in_seconds=3600)
                enviados.append(arquivo.id)
                blocos.append({"type": "document", "source": {"type": "file", "file_id": arquivo.id},
                               "title": caminho.name})
            logger.info("IA: %d documento(s) enviado(s)", len(enviados))
            yield ConversaClaude(cliente, self.modelo, self.esforco, blocos)
        finally:
            for file_id in enviados:
                with contextlib.suppress(anthropic.APIError):
                    cliente.files.delete(file_id)
            if enviados:
                logger.info("IA: documentos apagados da Anthropic")


PROVEDORES: dict[str, type[Provedor]] = {"claude": ProvedorClaude}
