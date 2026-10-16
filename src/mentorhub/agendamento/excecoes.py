"""Exceções do componente de Agendamento.

Cada uma corresponde a uma pré-condição violada nos contratos do documento.
"""

from __future__ import annotations


class ErroAgendamento(Exception):
    """Base de todos os erros do componente de Agendamento."""


class MentorNaoEncontrado(ErroAgendamento):
    """O mentor informado não existe no sistema."""


class MentoradoNaoEncontrado(ErroAgendamento):
    """O mentorado informado não existe no sistema."""


class HorarioIndisponivel(ErroAgendamento):
    """O horário escolhido não está livre na agenda do mentor."""


class SessaoNaoEncontrada(ErroAgendamento):
    """Não existe sessão com o ID informado."""


class CancelamentoNaoPermitido(ErroAgendamento):
    """A sessão não pode ser cancelada (já cancelada ou já aconteceu)."""
