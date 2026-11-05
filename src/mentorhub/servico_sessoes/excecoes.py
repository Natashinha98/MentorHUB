"""Erros do Serviço de Sessões de Mentoria.

Cada erro corresponde a uma condição de falha prevista no contrato do serviço e
carrega um `codigo` estável, usado na resposta da API.
"""

from __future__ import annotations


class ErroServicoSessoes(Exception):
    """Base dos erros do serviço."""

    codigo = "ERRO_SERVICO_SESSOES"


class DadosInvalidos(ErroServicoSessoes):
    """Falta algum parâmetro, o formato está errado ou o horário já passou."""

    codigo = "DADOS_INVALIDOS"


class MentorNaoEncontrado(ErroServicoSessoes):
    """O identificador não corresponde a um mentor."""

    codigo = "MENTOR_NAO_ENCONTRADO"


class MentoradoNaoEncontrado(ErroServicoSessoes):
    """O identificador não corresponde a um mentorado."""

    codigo = "MENTORADO_NAO_ENCONTRADO"


class HorarioIndisponivel(ErroServicoSessoes):
    """O horário não está na agenda do mentor ou já foi reservado."""

    codigo = "HORARIO_INDISPONIVEL"


class SessaoNaoEncontrada(ErroServicoSessoes):
    """Não existe sessão com o identificador informado."""

    codigo = "SESSAO_NAO_ENCONTRADA"


class CancelamentoNaoPermitido(ErroServicoSessoes):
    """A sessão já foi cancelada ou o horário dela já passou."""

    codigo = "CANCELAMENTO_NAO_PERMITIDO"


class AgendaIndisponivel(ErroServicoSessoes):
    """Não foi possível reservar ou liberar o horário na agenda do mentor."""

    codigo = "AGENDA_INDISPONIVEL"
