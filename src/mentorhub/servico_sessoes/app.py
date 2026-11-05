"""Monta o Serviço de Sessões com as implementações em memória (demonstração).

É o único arquivo que conhece as classes concretas: banco em memória, e-mail
simulado e componentes. O resto do serviço conhece só interfaces.

Dados iniciais:
  - mentores:   m1 (Ana Mentora), m2 (Carlos Mentor)
  - mentorados: a1 (Bruno Mentorado), a2 (Carla Mentorada)
  - agenda:     para os dois mentores, nos próximos 7 dias, horários livres às
                10:00, 14:00 e 16:00
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

from mentorhub.agendamento.componente import ComponenteAgendamento
from mentorhub.externos.email_simulado import EmailSimulado
from mentorhub.modelos import Papel, Usuario
from mentorhub.notificacoes.componente import ComponenteNotificacoes
from mentorhub.persistencia.memoria import PersistenciaEmMemoria
from mentorhub.servico_sessoes.api import criar_app
from mentorhub.servico_sessoes.servico import ServicoSessoesMentoria

MENTORES = [("m1", "Ana Mentora", "ana@mentorhub.com"), ("m2", "Carlos Mentor", "carlos@mentorhub.com")]
MENTORADOS = [("a1", "Bruno Mentorado", "bruno@mentorhub.com"), ("a2", "Carla Mentorada", "carla@mentorhub.com")]
HORAS_LIVRES = (time(10, 0), time(14, 0), time(16, 0))


def carregar_dados_iniciais(banco: PersistenciaEmMemoria, hoje: date, dias: int = 7) -> None:
    for mentor_id, nome, email in MENTORES:
        banco.salvar_usuario(Usuario(mentor_id, nome, email, Papel.MENTOR))
        for d in range(1, dias + 1):
            for hora in HORAS_LIVRES:
                banco.cadastrar_horario_livre(mentor_id, datetime.combine(hoje + timedelta(days=d), hora))
    for mentorado_id, nome, email in MENTORADOS:
        banco.salvar_usuario(Usuario(mentorado_id, nome, email, Papel.MENTORADO))


def montar_servico(
    agora: Callable[[], datetime] = datetime.now, imprimir_emails: bool = True
) -> tuple[ServicoSessoesMentoria, PersistenciaEmMemoria, EmailSimulado]:
    banco = PersistenciaEmMemoria()
    carregar_dados_iniciais(banco, agora().date())
    email = EmailSimulado(imprimir=imprimir_emails)
    notificacoes = ComponenteNotificacoes(email)
    agendamento = ComponenteAgendamento(banco, notificacoes, agora=agora)
    servico = ServicoSessoesMentoria(agendamento, banco, agora=agora)
    return servico, banco, email


app = criar_app(montar_servico()[0])
