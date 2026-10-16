"""Componente de Agendamento (core do MentorHub).

Controla a disponibilidade dos mentores e as sessões de mentoria. Pra isso ele
usa duas interfaces requeridas, entregues pelo construtor:
  - IPersistencia: salvar e consultar horários, sessões e usuários;
  - INotificacao: pedir o aviso por e-mail quando uma sessão muda de situação.

O componente conhece só as interfaces, nunca as classes que as implementam.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable
from uuid import uuid4

from mentorhub.agendamento.excecoes import (
    CancelamentoNaoPermitido,
    HorarioIndisponivel,
    MentoradoNaoEncontrado,
    MentorNaoEncontrado,
    SessaoNaoEncontrada,
)
from mentorhub.agendamento.interfaces import IAgendamento
from mentorhub.modelos import Papel, ResultadoEnvio, Sessao, StatusSessao, Usuario
from mentorhub.notificacoes.interfaces import INotificacao
from mentorhub.persistencia.interfaces import IPersistencia

logger = logging.getLogger(__name__)

_PedidoDeAviso = Callable[[str, str, str, datetime], ResultadoEnvio]


class ComponenteAgendamento(IAgendamento):
    """Implementa IAgendamento."""

    def __init__(
        self,
        persistencia: IPersistencia,
        notificacao: INotificacao,
        agora: Callable[[], datetime] = datetime.now,
    ) -> None:
        # `agora` existe pra os testes controlarem o relógio.
        self._persistencia = persistencia
        self._notificacao = notificacao
        self._agora = agora

    # ------------------------------------------------------------------ IAgendamento

    def verificar_disponibilidade(self, mentor_id: str, data: date) -> list[datetime]:
        self._buscar_mentor(mentor_id)
        return sorted(self._persistencia.listar_horarios_livres(mentor_id, data))

    def agendar_sessao(
        self, mentor_id: str, mentorado_id: str, horario: datetime
    ) -> Sessao:
        self._buscar_mentor(mentor_id)
        self._buscar_mentorado(mentorado_id)

        # Reserva o horário. Se não estava livre, nada foi alterado.
        if not self._persistencia.ocupar_horario(mentor_id, horario):
            raise HorarioIndisponivel(
                f"O horário {horario:%d/%m/%Y %H:%M} não está livre para o mentor {mentor_id}."
            )

        sessao = Sessao(
            id=str(uuid4()),
            mentor_id=mentor_id,
            mentorado_id=mentorado_id,
            horario=horario,
            status=StatusSessao.MARCADA,
        )
        try:
            self._persistencia.salvar_sessao(sessao)
        except Exception:
            # Não deixa o horário preso se a sessão não foi salva.
            self._persistencia.liberar_horario(mentor_id, horario)
            raise

        self._avisar(sessao, self._notificacao.enviar_notificacao_confirmacao)
        return sessao

    def cancelar_sessao(self, sessao_id: str) -> Sessao:
        sessao = self._persistencia.buscar_sessao(sessao_id)
        if sessao is None:
            raise SessaoNaoEncontrada(f"Sessão {sessao_id} não encontrada.")
        if sessao.status != StatusSessao.MARCADA:
            raise CancelamentoNaoPermitido(f"A sessão {sessao_id} já está {sessao.status.value}.")
        if sessao.horario <= self._agora():
            raise CancelamentoNaoPermitido(f"A sessão {sessao_id} já aconteceu.")

        sessao.status = StatusSessao.CANCELADA
        self._persistencia.salvar_sessao(sessao)
        self._persistencia.liberar_horario(sessao.mentor_id, sessao.horario)

        self._avisar(sessao, self._notificacao.enviar_notificacao_cancelamento)
        return sessao

    # ------------------------------------------------------------------ internos

    def _buscar_mentor(self, mentor_id: str) -> Usuario:
        usuario = self._persistencia.buscar_usuario(mentor_id)
        if usuario is None or usuario.papel != Papel.MENTOR:
            raise MentorNaoEncontrado(f"Mentor {mentor_id} não encontrado.")
        return usuario

    def _buscar_mentorado(self, mentorado_id: str) -> Usuario:
        usuario = self._persistencia.buscar_usuario(mentorado_id)
        if usuario is None or usuario.papel != Papel.MENTORADO:
            raise MentoradoNaoEncontrado(f"Mentorado {mentorado_id} não encontrado.")
        return usuario

    def _avisar(self, sessao: Sessao, pedir_aviso: _PedidoDeAviso) -> None:
        """Pede o aviso pro componente de Notificações.

        Uma falha aqui nunca desfaz o que já foi feito na sessão: o aviso é só
        registrado no log. É a regra escrita na pós-condição das operações.
        """
        mentor = self._persistencia.buscar_usuario(sessao.mentor_id)
        mentorado = self._persistencia.buscar_usuario(sessao.mentorado_id)
        if mentor is None or mentorado is None:
            logger.warning("Sessão %s sem dados dos usuários; aviso não enviado.", sessao.id)
            return
        try:
            resultado = pedir_aviso(sessao.id, mentor.email, mentorado.email, sessao.horario)
        except Exception:  # qualquer erro do aviso só vai pro log
            logger.exception("Erro ao pedir o aviso da sessão %s; a sessão foi mantida.", sessao.id)
            return
        if not resultado.enviado:
            logger.warning(
                "Aviso da sessão %s não foi entregue a todos: %s",
                sessao.id,
                "; ".join(resultado.falhas),
            )
