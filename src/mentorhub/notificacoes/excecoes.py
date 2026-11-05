"""Erros do componente de Notificações."""

from __future__ import annotations


class ErroNotificacao(Exception):
    """Base dos erros do componente de Notificações."""


class EmailInvalido(ErroNotificacao):
    """Um dos e-mails recebidos não tem formato válido (pré-condição violada)."""


class FalhaEnvioEmail(ErroNotificacao):
    """O serviço de e-mail não conseguiu entregar a mensagem."""
