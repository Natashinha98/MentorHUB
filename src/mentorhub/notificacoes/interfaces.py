"""Interfaces do componente de Notificações.

- INotificacao: interface fornecida (usada pelo Agendamento).
- IEmail: interface requerida (o serviço de e-mail que realmente envia a mensagem).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from mentorhub.modelos import ResultadoEnvio


class INotificacao(ABC):
    """Avisos sobre sessões de mentoria."""

    @abstractmethod
    def enviar_notificacao_confirmacao(
        self, sessao_id: str, email_mentor: str, email_mentorado: str, data_hora: datetime
    ) -> ResultadoEnvio:
        """Avisa mentor e mentorado que a sessão foi confirmada.

        Pré-condição:  os dois e-mails têm formato válido (senão EmailInvalido,
                       e nada é enviado).
        Saída:         ResultadoEnvio (enviado=True só se os dois receberam).
        Pós-condição:  uma falha com um destinatário não impede o aviso ao outro.
        """

    @abstractmethod
    def enviar_notificacao_cancelamento(
        self, sessao_id: str, email_mentor: str, email_mentorado: str, data_hora: datetime
    ) -> ResultadoEnvio:
        """Avisa mentor e mentorado que a sessão foi cancelada.

        Mesmas pré e pós-condições do aviso de confirmação.
        """


class IEmail(ABC):
    """Serviço de e-mail usado pelas Notificações (no projeto, um serviço externo)."""

    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        """Envia uma mensagem. Se não conseguir, levanta FalhaEnvioEmail."""
