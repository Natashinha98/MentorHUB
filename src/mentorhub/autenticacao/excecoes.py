"""Erros do componente de Autenticação."""

from __future__ import annotations


class ErroAutenticacao(Exception):
    """Base dos erros do componente de Autenticação."""


class DadosInvalidos(ErroAutenticacao):
    """Os dados enviados não respeitam as regras (pré-condição violada).

    `erros` traz uma frase pra cada regra desrespeitada.
    """

    def __init__(self, erros: tuple[str, ...]) -> None:
        super().__init__("; ".join(erros))
        self.erros = erros


class CredenciaisInvalidas(ErroAutenticacao):
    """E-mail ou senha incorretos. A mensagem é a mesma nos dois casos, de propósito."""

    def __init__(self) -> None:
        super().__init__("E-mail ou senha incorretos.")


class ContaNaoEncontrada(ErroAutenticacao):
    """Não existe conta com o e-mail informado."""


class CodigoRecuperacaoInvalido(ErroAutenticacao):
    """O código de recuperação está errado, já foi usado ou venceu."""
