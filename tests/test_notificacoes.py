"""Testes do componente de Notificações, isolado (o serviço de e-mail é simulado)."""

from __future__ import annotations

import pytest
from apoio import EMAIL_MENTOR, EMAIL_MENTORADO, H10

from mentorhub.externos.email_simulado import EmailSimulado
from mentorhub.notificacoes.componente import ComponenteNotificacoes
from mentorhub.notificacoes.excecoes import EmailInvalido
from mentorhub.notificacoes.interfaces import IEmail, INotificacao

SESSAO_ID = "sessao-123"
EMAILS_INVALIDOS = ["", "sem-arroba", "a@b", "a b@c.com", None]


def test_componente_implementa_a_interface_fornecida(notificacoes):
    assert isinstance(notificacoes, INotificacao)


def test_interfaces_nao_podem_ser_instanciadas():
    with pytest.raises(TypeError):
        INotificacao()
    with pytest.raises(TypeError):
        IEmail()


# ------------------------------------------------------ enviar_notificacao_confirmacao


def test_confirmacao_envia_para_o_mentor_e_para_o_mentorado(notificacoes, email):
    resultado = notificacoes.enviar_notificacao_confirmacao(
        SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10
    )

    assert resultado.enviado is True
    assert resultado.falhas == ()
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]


def test_confirmacao_tem_codigo_data_e_hora_da_sessao(notificacoes, email):
    notificacoes.enviar_notificacao_confirmacao(SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10)

    for enviado in email.enviados:
        assert "confirmada" in enviado.assunto.lower()
        assert SESSAO_ID in enviado.corpo
        assert "10/01/2030" in enviado.corpo
        assert "10:00" in enviado.corpo


@pytest.mark.parametrize("invalido", EMAILS_INVALIDOS)
def test_confirmacao_com_email_do_mentor_invalido_levanta_erro_e_nao_envia(
    notificacoes, email, invalido
):
    with pytest.raises(EmailInvalido):
        notificacoes.enviar_notificacao_confirmacao(SESSAO_ID, invalido, EMAIL_MENTORADO, H10)
    assert email.enviados == []


@pytest.mark.parametrize("invalido", EMAILS_INVALIDOS)
def test_confirmacao_com_email_do_mentorado_invalido_nao_envia_nem_pro_mentor(
    notificacoes, email, invalido
):
    with pytest.raises(EmailInvalido):
        notificacoes.enviar_notificacao_confirmacao(SESSAO_ID, EMAIL_MENTOR, invalido, H10)
    assert email.enviados == []


# ------------------------------------------------------ enviar_notificacao_cancelamento


def test_cancelamento_envia_para_o_mentor_e_para_o_mentorado(notificacoes, email):
    resultado = notificacoes.enviar_notificacao_cancelamento(
        SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10
    )

    assert resultado.enviado is True
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]


def test_cancelamento_diz_que_a_sessao_foi_cancelada(notificacoes, email):
    notificacoes.enviar_notificacao_cancelamento(SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10)

    for enviado in email.enviados:
        assert "cancelada" in enviado.assunto.lower()
        assert SESSAO_ID in enviado.corpo
        assert "10/01/2030" in enviado.corpo
        assert "10:00" in enviado.corpo


def test_cancelamento_com_email_invalido_levanta_erro_e_nao_envia(notificacoes, email):
    with pytest.raises(EmailInvalido):
        notificacoes.enviar_notificacao_cancelamento(SESSAO_ID, EMAIL_MENTOR, "invalido", H10)
    assert email.enviados == []


# ------------------------------------------------------------------- falhas no envio


def test_servico_de_email_fora_do_ar_devolve_falhou(email, notificacoes):
    email.fora_do_ar = True

    resultado = notificacoes.enviar_notificacao_confirmacao(
        SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10
    )

    assert resultado.enviado is False
    assert len(resultado.falhas) == 2
    assert email.enviados == []


def test_falha_com_um_destinatario_nao_impede_o_aviso_do_outro():
    email = EmailSimulado(destinatarios_com_falha=[EMAIL_MENTOR])
    notificacoes = ComponenteNotificacoes(email)

    resultado = notificacoes.enviar_notificacao_cancelamento(
        SESSAO_ID, EMAIL_MENTOR, EMAIL_MENTORADO, H10
    )

    assert resultado.enviado is False
    assert len(resultado.falhas) == 1 and EMAIL_MENTOR in resultado.falhas[0]
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTORADO]
