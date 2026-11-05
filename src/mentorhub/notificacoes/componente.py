"""Componente de Notificações.

Monta as mensagens de confirmação e de cancelamento e pede o envio pela interface
IEmail, que recebe pelo construtor. Não conhece a classe que implementa o e-mail.
"""

from __future__ import annotations

import re
from datetime import datetime

from mentorhub.modelos import ResultadoEnvio
from mentorhub.notificacoes.excecoes import EmailInvalido, FalhaEnvioEmail
from mentorhub.notificacoes.interfaces import IEmail, INotificacao

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ComponenteNotificacoes(INotificacao):
    """Implementa INotificacao."""

    def __init__(self, email: IEmail) -> None:
        self._email = email

    def enviar_notificacao_confirmacao(
        self, sessao_id: str, email_mentor: str, email_mentorado: str, data_hora: datetime
    ) -> ResultadoEnvio:
        assunto = "MentorHub: sessão de mentoria confirmada"
        corpo = (
            f"A sessão {sessao_id} foi confirmada para "
            f"{data_hora:%d/%m/%Y} às {data_hora:%H:%M}."
        )
        return self._enviar_para_os_dois(email_mentor, email_mentorado, assunto, corpo)

    def enviar_notificacao_cancelamento(
        self, sessao_id: str, email_mentor: str, email_mentorado: str, data_hora: datetime
    ) -> ResultadoEnvio:
        assunto = "MentorHub: sessão de mentoria cancelada"
        corpo = (
            f"A sessão {sessao_id}, marcada para {data_hora:%d/%m/%Y} às "
            f"{data_hora:%H:%M}, foi cancelada."
        )
        return self._enviar_para_os_dois(email_mentor, email_mentorado, assunto, corpo)

    def _enviar_para_os_dois(
        self, email_mentor: str, email_mentorado: str, assunto: str, corpo: str
    ) -> ResultadoEnvio:
        # Confere os dois antes de enviar qualquer coisa: com um e-mail inválido,
        # ninguém recebe aviso pela metade.
        for email in (email_mentor, email_mentorado):
            if not isinstance(email, str) or not _EMAIL.match(email):
                raise EmailInvalido(f"E-mail inválido: {email!r}.")

        falhas: list[str] = []
        for destinatario in (email_mentor, email_mentorado):
            try:
                self._email.enviar(destinatario, assunto, corpo)
            except FalhaEnvioEmail as erro:
                falhas.append(f"{destinatario}: {erro}")
        return ResultadoEnvio(enviado=not falhas, falhas=tuple(falhas))
