"""Testes da integração: Agendamento usando o componente de Notificações de verdade.

Aqui nada é espiã. O Agendamento chama a interface INotificacao, quem responde é o
ComponenteNotificacoes, e o e-mail cai no EmailSimulado, onde dá pra conferir o resultado.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from apoio import (
    DIA,
    EMAIL_MENTOR,
    EMAIL_MENTORADO,
    H10,
    H11,
    MENTOR_ID,
    MENTORADO_ID,
)

from mentorhub.agendamento.componente import ComponenteAgendamento
from mentorhub.agendamento.excecoes import HorarioIndisponivel
from mentorhub.modelos import Papel, StatusSessao, Usuario

SRC = Path(__file__).resolve().parents[1] / "src"


def test_agendar_dispara_email_de_confirmacao_pro_mentor_e_pro_mentorado(
    agendamento_integrado, email
):
    sessao = agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]
    for enviado in email.enviados:
        assert "confirmada" in enviado.assunto.lower()
        assert sessao.id in enviado.corpo
        assert "10/01/2030" in enviado.corpo and "10:00" in enviado.corpo


def test_cancelar_dispara_email_de_cancelamento_pro_mentor_e_pro_mentorado(
    agendamento_integrado, email
):
    sessao = agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    email.enviados.clear()

    agendamento_integrado.cancelar_sessao(sessao.id)

    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]
    for enviado in email.enviados:
        assert "cancelada" in enviado.assunto.lower()
        assert sessao.id in enviado.corpo


def test_fluxo_completo_verificar_agendar_cancelar(agendamento_integrado, email):
    assert agendamento_integrado.verificar_disponibilidade(MENTOR_ID, DIA) == [H10, H11]

    sessao = agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    assert agendamento_integrado.verificar_disponibilidade(MENTOR_ID, DIA) == [H11]
    assert len(email.enviados) == 2

    cancelada = agendamento_integrado.cancelar_sessao(sessao.id)
    assert cancelada.status == StatusSessao.CANCELADA
    assert agendamento_integrado.verificar_disponibilidade(MENTOR_ID, DIA) == [H10, H11]
    assert len(email.enviados) == 4


def test_dois_agendamentos_do_mesmo_horario_so_o_primeiro_funciona(
    agendamento_integrado, email
):
    agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    with pytest.raises(HorarioIndisponivel):
        agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert len(email.enviados) == 2  # só os avisos do primeiro agendamento


def test_servico_de_email_fora_do_ar_nao_desfaz_o_agendamento(
    agendamento_integrado, persistencia, email, caplog
):
    email.fora_do_ar = True

    with caplog.at_level(logging.WARNING):
        sessao = agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.MARCADA
    assert H10 not in agendamento_integrado.verificar_disponibilidade(MENTOR_ID, DIA)
    assert email.enviados == []
    assert "não foi entregue" in caplog.text


def test_email_invalido_no_cadastro_do_mentor_nao_desfaz_o_agendamento(
    agendamento_integrado, persistencia, email, caplog
):
    # O erro de pré-condição (EmailInvalido) nasce dentro de Notificações,
    # e o Agendamento precisa segurar esse erro sem perder a sessão.
    persistencia.salvar_usuario(Usuario("m2", "Carlos", "carlos-sem-arroba", Papel.MENTOR))
    persistencia.cadastrar_horario_livre("m2", H10)

    with caplog.at_level(logging.ERROR):
        sessao = agendamento_integrado.agendar_sessao("m2", MENTORADO_ID, H10)

    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.MARCADA
    assert email.enviados == []
    assert "Erro ao pedir o aviso" in caplog.text


def test_cancelamento_com_email_fora_do_ar_nao_desfaz_o_cancelamento(
    agendamento_integrado, persistencia, email
):
    sessao = agendamento_integrado.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    email.fora_do_ar = True

    cancelada = agendamento_integrado.cancelar_sessao(sessao.id)

    assert cancelada.status == StatusSessao.CANCELADA
    assert H10 in agendamento_integrado.verificar_disponibilidade(MENTOR_ID, DIA)


# ------------------------------------------- os componentes só dependem das interfaces


@pytest.mark.parametrize(
    "importado, proibidos",
    [
        (
            "mentorhub.agendamento.componente",
            [
                "mentorhub.notificacoes.componente",
                "mentorhub.persistencia.memoria",
                "mentorhub.externos.email_simulado",
            ],
        ),
        (
            "mentorhub.notificacoes.componente",
            ["mentorhub.agendamento.componente", "mentorhub.externos.email_simulado"],
        ),
        (
            "mentorhub.autenticacao.componente",
            [
                "mentorhub.agendamento.componente",
                "mentorhub.busca.componente",
                "mentorhub.persistencia.memoria",
            ],
        ),
        (
            "mentorhub.busca.componente",
            [
                "mentorhub.agendamento.componente",
                "mentorhub.autenticacao.componente",
                "mentorhub.persistencia.memoria",
                "mentorhub.armazenamento.memoria",
            ],
        ),
    ],
)
def test_componente_nao_importa_a_implementacao_do_outro(importado, proibidos):
    """Roda num Python limpo pra ver o que realmente é importado."""
    codigo = (
        f"import sys, {importado}\n"
        f"achados = [m for m in {proibidos!r} if m in sys.modules]\n"
        "print(achados)\n"
        "sys.exit(1 if achados else 0)\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"importou implementações: {resultado.stdout}{resultado.stderr}"


# ------------------------- Autenticação e Busca de Mentores com o Agendamento


def test_usuario_criado_na_autenticacao_consegue_agendar(persistencia, notificacoes, email, relogio):
    """Os componentes só se falam pelo banco compartilhado: quem cria a conta é a
    Autenticação, e o Agendamento enxerga esse usuário pela IPersistencia."""
    from mentorhub.autenticacao.componente import ComponenteAutenticacao

    autenticacao = ComponenteAutenticacao(persistencia, iteracoes_hash=1_000)
    agendamento = ComponenteAgendamento(persistencia, notificacoes, agora=relogio)

    novo = autenticacao.criar_conta("Carla Nova", "carla@mentorhub.com", "senha1234", Papel.MENTORADO)
    sessao = agendamento.agendar_sessao(MENTOR_ID, novo.id, H10)

    assert sessao.mentorado_id == novo.id
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, "carla@mentorhub.com"]


def test_fluxo_login_busca_perfil_e_agendamento(persistencia, notificacoes, email, relogio, imagens):
    """O caminho do mentorado: entra, procura mentor, abre o perfil e agenda."""
    from mentorhub.autenticacao.componente import ComponenteAutenticacao
    from mentorhub.busca.componente import ComponenteBuscaMentores
    from mentorhub.modelos import PerfilMentor

    persistencia.salvar_perfil_mentor(PerfilMentor(MENTOR_ID, ("Python",), "Bio da Ana."))
    autenticacao = ComponenteAutenticacao(persistencia, iteracoes_hash=1_000)
    busca = ComponenteBuscaMentores(persistencia, imagens)
    agendamento = ComponenteAgendamento(persistencia, notificacoes, agora=relogio)

    autenticacao.criar_conta("Carla Nova", "carla@mentorhub.com", "senha1234", Papel.MENTORADO)
    mentorado = autenticacao.autenticar_usuario("carla@mentorhub.com", "senha1234")
    escolhido = busca.pesquisar_mentores("python")[0]
    perfil = busca.consultar_perfil(escolhido.mentor_id)
    horario = agendamento.verificar_disponibilidade(perfil.resumo.mentor_id, DIA)[0]
    sessao = agendamento.agendar_sessao(perfil.resumo.mentor_id, mentorado.id, horario)

    assert sessao.status == StatusSessao.MARCADA
    assert len(email.enviados) == 2
