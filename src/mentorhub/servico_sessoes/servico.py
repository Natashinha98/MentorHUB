"""Serviço de Sessões de Mentoria.

Realiza o contrato do serviço especificado no LAB07:
  - agendar_sessao   (agendarSessao)
  - cancelar_sessao  (cancelarSessao)
  - consultar_sessao (consultarSessao)

As regras de agenda já existentes ficam no componente de Agendamento, que o serviço
recebe pela interface IAgendamento. O serviço acrescenta o que o contrato pede a mais:
validação dos dados, horário posterior ao momento da solicitação, a consulta da
sessão e a tradução de cada falha para um erro do contrato.

Assim como os componentes, o serviço conhece só interfaces, nunca as classes que as
implementam (quem monta tudo é `app.py`).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable

from mentorhub.agendamento import excecoes as erros_agenda
from mentorhub.agendamento.interfaces import IAgendamento
from mentorhub.modelos import Sessao
from mentorhub.persistencia.interfaces import IPersistencia
from mentorhub.servico_sessoes.excecoes import (
    AgendaIndisponivel,
    CancelamentoNaoPermitido,
    DadosInvalidos,
    ErroServicoSessoes,
    HorarioIndisponivel,
    MentoradoNaoEncontrado,
    MentorNaoEncontrado,
    SessaoNaoEncontrada,
)

logger = logging.getLogger(__name__)

# Erro do componente de Agendamento -> erro do contrato do serviço.
_TRADUCAO = {
    erros_agenda.MentorNaoEncontrado: MentorNaoEncontrado,
    erros_agenda.MentoradoNaoEncontrado: MentoradoNaoEncontrado,
    erros_agenda.HorarioIndisponivel: HorarioIndisponivel,
    erros_agenda.SessaoNaoEncontrada: SessaoNaoEncontrada,
    erros_agenda.CancelamentoNaoPermitido: CancelamentoNaoPermitido,
}


class ServicoSessoesMentoria:
    """Implementa as operações do Serviço de Sessões de Mentoria."""

    def __init__(
        self,
        agendamento: IAgendamento,
        persistencia: IPersistencia,
        agora: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._agendamento = agendamento
        self._persistencia = persistencia
        self._agora = agora

    # ------------------------------------------------------------------ operações

    def agendar_sessao(self, mentor_id: str, mentorado_id: str, horario: datetime) -> Sessao:
        """agendarSessao(): marca uma sessão em um horário livre do mentor."""
        self._exigir_texto(mentor_id, "mentorId")
        self._exigir_texto(mentorado_id, "mentoradoId")
        if not isinstance(horario, datetime):
            raise DadosInvalidos("O campo horario é obrigatório e deve ser uma data e hora.")
        if horario <= self._agora():
            raise DadosInvalidos("O horário precisa ser posterior ao momento da solicitação.")
        return self._executar(
            lambda: self._agendamento.agendar_sessao(mentor_id, mentorado_id, horario),
            "Não foi possível confirmar a reserva do horário na agenda do mentor.",
        )

    def cancelar_sessao(self, sessao_id: str) -> Sessao:
        """cancelarSessao(): cancela uma sessão marcada que ainda não aconteceu."""
        self._exigir_texto(sessao_id, "sessaoId")
        return self._executar(
            lambda: self._agendamento.cancelar_sessao(sessao_id),
            "Não foi possível liberar o horário na agenda do mentor.",
        )

    def consultar_sessao(self, sessao_id: str) -> Sessao:
        """consultarSessao(): informa os dados e a situação de uma sessão (não altera nada)."""
        self._exigir_texto(sessao_id, "sessaoId")
        sessao = self._persistencia.buscar_sessao(sessao_id)
        if sessao is None:
            raise SessaoNaoEncontrada(f"Sessão {sessao_id} não encontrada.")
        return sessao

    def verificar_disponibilidade(self, mentor_id: str, data: date) -> list[datetime]:
        """Apoio para os testes da API: horários livres do mentor numa data.

        Pertence ao Serviço de Disponibilidade; aqui só repassa ao componente.
        """
        self._exigir_texto(mentor_id, "mentorId")
        return self._executar(
            lambda: self._agendamento.verificar_disponibilidade(mentor_id, data),
            "Não foi possível consultar a agenda do mentor.",
        )

    # ------------------------------------------------------------------ internos

    @staticmethod
    def _exigir_texto(valor: object, campo: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise DadosInvalidos(f"O campo {campo} é obrigatório.")

    @staticmethod
    def _executar(operacao: Callable, mensagem_indisponivel: str):
        """Roda a operação no componente e traduz as falhas para o contrato."""
        try:
            return operacao()
        except erros_agenda.ErroAgendamento as erro:
            raise _TRADUCAO.get(type(erro), ErroServicoSessoes)(str(erro)) from erro
        except Exception as erro:  # falha de infraestrutura (agenda/banco fora do ar)
            logger.exception("Falha ao acessar a agenda: %s", erro)
            raise AgendaIndisponivel(mensagem_indisponivel) from erro
