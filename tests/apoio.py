"""Dados e classes de apoio usados pelos testes."""

from __future__ import annotations

from datetime import date, datetime

from mentorhub.modelos import ResultadoEnvio
from mentorhub.notificacoes.interfaces import INotificacao

MENTOR_ID = "m1"
MENTORADO_ID = "a1"
EMAIL_MENTOR = "ana@mentorhub.com"
EMAIL_MENTORADO = "bruno@mentorhub.com"

DIA = date(2030, 1, 10)
H10 = datetime(2030, 1, 10, 10, 0)
H11 = datetime(2030, 1, 10, 11, 0)
OUTRO_DIA_H9 = datetime(2030, 1, 11, 9, 0)
HORARIO_FORA_DA_AGENDA = datetime(2030, 1, 10, 15, 0)

AGORA_INICIAL = datetime(2030, 1, 1, 12, 0)


class Relogio:
    """Relógio controlável: o teste muda `agora` quando quiser."""

    def __init__(self, agora: datetime) -> None:
        self.agora = agora

    def __call__(self) -> datetime:
        return self.agora


class NotificacaoEspia(INotificacao):
    """INotificacao falsa que só anota o que o Agendamento pediu.

    Serve pra testar o Agendamento sozinho, sem o componente de Notificações de verdade.
    """

    def __init__(self) -> None:
        self.confirmacoes: list[tuple] = []
        self.cancelamentos: list[tuple] = []
        self.resultado = ResultadoEnvio(enviado=True)
        self.erro: Exception | None = None

    def _registrar(self, lista: list[tuple], pedido: tuple) -> ResultadoEnvio:
        lista.append(pedido)
        if self.erro is not None:
            raise self.erro
        return self.resultado

    def enviar_notificacao_confirmacao(
        self, sessao_id, email_mentor, email_mentorado, data_hora
    ) -> ResultadoEnvio:
        return self._registrar(
            self.confirmacoes, (sessao_id, email_mentor, email_mentorado, data_hora)
        )

    def enviar_notificacao_cancelamento(
        self, sessao_id, email_mentor, email_mentorado, data_hora
    ) -> ResultadoEnvio:
        return self._registrar(
            self.cancelamentos, (sessao_id, email_mentor, email_mentorado, data_hora)
        )
