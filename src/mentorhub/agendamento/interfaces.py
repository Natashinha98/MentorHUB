"""Interface fornecida pelo componente de Agendamento: IAgendamento.

As interfaces que o Agendamento requer ficam com quem as fornece:
  - IPersistencia -> mentorhub/persistencia/interfaces.py
  - INotificacao  -> mentorhub/notificacoes/interfaces.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from mentorhub.modelos import Sessao


class IAgendamento(ABC):
    """Operações de agenda e de sessões de mentoria."""

    @abstractmethod
    def verificar_disponibilidade(self, mentor_id: str, data: date) -> list[datetime]:
        """Lista os horários livres do mentor numa data.

        Pré-condição:  o mentor precisa existir (senão MentorNaoEncontrado).
        Saída:         lista de horários livres, em ordem (pode vir vazia).
        Pós-condição:  nada é alterado, é só uma consulta.
        """

    @abstractmethod
    def agendar_sessao(
        self, mentor_id: str, mentorado_id: str, horario: datetime
    ) -> Sessao:
        """Marca uma sessão de mentoria.

        Pré-condição:  o horário precisa estar livre na agenda do mentor
                       (senão HorarioIndisponivel). Mentor e mentorado precisam
                       existir (senão MentorNaoEncontrado / MentoradoNaoEncontrado).
        Saída:         a sessão confirmada.
        Pós-condição:  a sessão fica marcada e o horário deixa de ficar livre.
                       A INotificacao é chamada pra avisar os dois e, se o aviso
                       falhar, o agendamento não é desfeito.
        """

    @abstractmethod
    def cancelar_sessao(self, sessao_id: str) -> Sessao:
        """Cancela uma sessão marcada.

        Pré-condição:  a sessão precisa existir (senão SessaoNaoEncontrada), estar
                       marcada e ainda não ter acontecido (senão CancelamentoNaoPermitido).
        Saída:         a sessão com status cancelada.
        Pós-condição:  a sessão fica cancelada e o horário volta a ficar livre.
                       A INotificacao é chamada pra avisar os dois.
        """
