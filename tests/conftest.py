"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import pytest
from apoio import (
    AGORA_INICIAL,
    EMAIL_MENTOR,
    EMAIL_MENTORADO,
    H10,
    H11,
    MENTOR_ID,
    MENTORADO_ID,
    OUTRO_DIA_H9,
    NotificacaoEspia,
    Relogio,
)

from mentorhub.agendamento.componente import ComponenteAgendamento
from mentorhub.externos.email_simulado import EmailSimulado
from mentorhub.modelos import Papel, Usuario
from mentorhub.notificacoes.componente import ComponenteNotificacoes
from mentorhub.persistencia.memoria import PersistenciaEmMemoria


@pytest.fixture
def persistencia() -> PersistenciaEmMemoria:
    """Banco em memória com um mentor, um mentorado e três horários livres."""
    banco = PersistenciaEmMemoria()
    banco.salvar_usuario(Usuario(MENTOR_ID, "Ana Mentora", EMAIL_MENTOR, Papel.MENTOR))
    banco.salvar_usuario(Usuario(MENTORADO_ID, "Bruno Mentorado", EMAIL_MENTORADO, Papel.MENTORADO))
    # Cadastrados fora de ordem de propósito, pra testar a ordenação.
    for horario in (H11, OUTRO_DIA_H9, H10):
        banco.cadastrar_horario_livre(MENTOR_ID, horario)
    return banco


@pytest.fixture
def relogio() -> Relogio:
    return Relogio(AGORA_INICIAL)


@pytest.fixture
def espia() -> NotificacaoEspia:
    return NotificacaoEspia()


@pytest.fixture
def agendamento(persistencia, espia, relogio) -> ComponenteAgendamento:
    """Agendamento sozinho: a notificação é uma espiã (teste isolado)."""
    return ComponenteAgendamento(persistencia, espia, agora=relogio)


@pytest.fixture
def email() -> EmailSimulado:
    return EmailSimulado()


@pytest.fixture
def notificacoes(email) -> ComponenteNotificacoes:
    return ComponenteNotificacoes(email)


@pytest.fixture
def agendamento_integrado(persistencia, notificacoes, relogio) -> ComponenteAgendamento:
    """Agendamento ligado ao componente de Notificações de verdade."""
    return ComponenteAgendamento(persistencia, notificacoes, agora=relogio)


# ------------------------------------------------ Autenticação e Busca de Mentores

from datetime import datetime  # noqa: E402

from mentorhub.armazenamento.memoria import ArmazenamentoEmMemoria  # noqa: E402
from mentorhub.autenticacao.componente import ComponenteAutenticacao  # noqa: E402
from mentorhub.busca.componente import ComponenteBuscaMentores  # noqa: E402
from mentorhub.modelos import Avaliacao, Foto, PerfilMentor  # noqa: E402


@pytest.fixture
def banco():
    """Banco em memória vazio, pros testes de contas e de busca."""
    return PersistenciaEmMemoria()


@pytest.fixture
def agora_auth() -> Relogio:
    return Relogio(datetime(2030, 1, 1, 12, 0))


@pytest.fixture
def autenticacao(banco, agora_auth) -> ComponenteAutenticacao:
    # Poucas iterações de hash: o teste fica rápido e o comportamento é o mesmo.
    return ComponenteAutenticacao(banco, agora=agora_auth, iteracoes_hash=1_000)


@pytest.fixture
def imagens() -> ArmazenamentoEmMemoria:
    return ArmazenamentoEmMemoria()


@pytest.fixture
def busca(banco, imagens) -> ComponenteBuscaMentores:
    """Busca com três mentores: Ana (nota 5,0), Carlos (4,0) e Dora (sem avaliações)."""
    for mentor_id, nome, areas in [
        ("m1", "Ana Mentora", ("Python", "Engenharia de Software")),
        ("m2", "Carlos Mentor", ("Dados", "Python")),
        ("m3", "Dora Mentora", ("Carreira",)),
    ]:
        banco.salvar_usuario(Usuario(mentor_id, nome, f"{mentor_id}@mentorhub.com", Papel.MENTOR))
        banco.salvar_perfil_mentor(PerfilMentor(mentor_id, areas, f"Bio de {nome}."))
    banco.salvar_usuario(Usuario("a1", "Bruno Mentorado", "bruno@mentorhub.com", Papel.MENTORADO))
    banco.salvar_avaliacao(Avaliacao("m1", "a1", "Bruno", 5, "Ótima mentoria."))
    banco.salvar_avaliacao(Avaliacao("m2", "a1", "Bruno", 4, "Bom."))
    imagens.salvar_foto("m1", Foto("image/png", b"png-da-ana"))
    return ComponenteBuscaMentores(banco, imagens)
