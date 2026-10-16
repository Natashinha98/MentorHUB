"""Testes do componente de Agendamento, isolado (a notificação é uma espiã).

Cada grupo de testes confere os contratos da operação: pré-condição, saída e pós-condição.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import pytest
from apoio import (
    DIA,
    EMAIL_MENTOR,
    EMAIL_MENTORADO,
    H10,
    H11,
    HORARIO_FORA_DA_AGENDA,
    MENTOR_ID,
    MENTORADO_ID,
    OUTRO_DIA_H9,
)

from mentorhub.agendamento.componente import ComponenteAgendamento
from mentorhub.agendamento.excecoes import (
    CancelamentoNaoPermitido,
    ErroAgendamento,
    HorarioIndisponivel,
    MentoradoNaoEncontrado,
    MentorNaoEncontrado,
    SessaoNaoEncontrada,
)
from mentorhub.agendamento.interfaces import IAgendamento
from mentorhub.modelos import ResultadoEnvio, StatusSessao


def test_componente_implementa_a_interface_fornecida(agendamento):
    assert isinstance(agendamento, IAgendamento)


def test_interface_nao_pode_ser_instanciada():
    with pytest.raises(TypeError):
        IAgendamento()


# ------------------------------------------------------------- verificar_disponibilidade


def test_lista_os_horarios_livres_da_data_em_ordem(agendamento):
    assert agendamento.verificar_disponibilidade(MENTOR_ID, DIA) == [H10, H11]


def test_nao_mostra_horarios_de_outra_data(agendamento):
    assert agendamento.verificar_disponibilidade(MENTOR_ID, DIA) == [H10, H11]
    assert agendamento.verificar_disponibilidade(MENTOR_ID, OUTRO_DIA_H9.date()) == [OUTRO_DIA_H9]


def test_data_sem_horarios_devolve_lista_vazia(agendamento):
    assert agendamento.verificar_disponibilidade(MENTOR_ID, date(2030, 2, 1)) == []


def test_mentor_inexistente_levanta_erro(agendamento):
    with pytest.raises(MentorNaoEncontrado):
        agendamento.verificar_disponibilidade("nao-existe", DIA)


def test_id_de_mentorado_nao_vale_como_mentor(agendamento):
    with pytest.raises(MentorNaoEncontrado):
        agendamento.verificar_disponibilidade(MENTORADO_ID, DIA)


def test_consulta_nao_altera_nada(agendamento, persistencia, espia):
    antes = persistencia.listar_horarios_livres(MENTOR_ID, DIA)
    agendamento.verificar_disponibilidade(MENTOR_ID, DIA)
    agendamento.verificar_disponibilidade(MENTOR_ID, DIA)
    assert persistencia.listar_horarios_livres(MENTOR_ID, DIA) == antes
    assert espia.confirmacoes == [] and espia.cancelamentos == []


# ------------------------------------------------------------------------ agendar_sessao


def test_agendar_cria_sessao_marcada(agendamento, persistencia):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert sessao.status == StatusSessao.MARCADA
    assert sessao.mentor_id == MENTOR_ID
    assert sessao.mentorado_id == MENTORADO_ID
    assert sessao.horario == H10
    salva = persistencia.buscar_sessao(sessao.id)
    assert salva is not None and salva.status == StatusSessao.MARCADA


def test_horario_agendado_deixa_de_ficar_livre(agendamento):
    agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    assert agendamento.verificar_disponibilidade(MENTOR_ID, DIA) == [H11]


def test_agendar_pede_notificacao_de_confirmacao_com_os_dados_certos(agendamento, espia):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert espia.confirmacoes == [(sessao.id, EMAIL_MENTOR, EMAIL_MENTORADO, H10)]
    assert espia.cancelamentos == []


def test_horario_ja_agendado_levanta_erro(agendamento):
    agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    with pytest.raises(HorarioIndisponivel):
        agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)


def test_horario_que_nao_esta_na_agenda_levanta_erro(agendamento):
    with pytest.raises(HorarioIndisponivel):
        agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, HORARIO_FORA_DA_AGENDA)


def test_horario_indisponivel_nao_pede_notificacao(agendamento, espia):
    with pytest.raises(HorarioIndisponivel):
        agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, HORARIO_FORA_DA_AGENDA)
    assert espia.confirmacoes == []


def test_mentor_inexistente_ao_agendar(agendamento):
    with pytest.raises(MentorNaoEncontrado):
        agendamento.agendar_sessao("nao-existe", MENTORADO_ID, H10)


def test_mentorado_inexistente_ao_agendar_nao_consome_o_horario(agendamento):
    with pytest.raises(MentoradoNaoEncontrado):
        agendamento.agendar_sessao(MENTOR_ID, "nao-existe", H10)
    assert H10 in agendamento.verificar_disponibilidade(MENTOR_ID, DIA)


def test_id_de_mentor_nao_vale_como_mentorado(agendamento):
    with pytest.raises(MentoradoNaoEncontrado):
        agendamento.agendar_sessao(MENTOR_ID, MENTOR_ID, H10)


def test_todos_os_erros_do_agendamento_tem_a_mesma_base():
    for erro in (
        MentorNaoEncontrado,
        MentoradoNaoEncontrado,
        HorarioIndisponivel,
        SessaoNaoEncontrada,
        CancelamentoNaoPermitido,
    ):
        assert issubclass(erro, ErroAgendamento)


def test_falha_no_aviso_nao_desfaz_o_agendamento(agendamento, persistencia, espia, caplog):
    espia.erro = RuntimeError("notificações fora do ar")

    with caplog.at_level(logging.ERROR):
        sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.MARCADA
    assert H10 not in agendamento.verificar_disponibilidade(MENTOR_ID, DIA)
    assert "Erro ao pedir o aviso" in caplog.text


def test_aviso_nao_entregue_nao_desfaz_o_agendamento(agendamento, persistencia, espia, caplog):
    espia.resultado = ResultadoEnvio(enviado=False, falhas=("ana@mentorhub.com: sem sinal",))

    with caplog.at_level(logging.WARNING):
        sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.MARCADA
    assert "não foi entregue" in caplog.text


def test_horario_volta_a_ficar_livre_se_a_sessao_nao_puder_ser_salva(
    agendamento, persistencia, monkeypatch
):
    def salvar_com_erro(sessao):
        raise OSError("banco fora do ar")

    monkeypatch.setattr(persistencia, "salvar_sessao", salvar_com_erro)

    with pytest.raises(OSError):
        agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    assert H10 in agendamento.verificar_disponibilidade(MENTOR_ID, DIA)


# ----------------------------------------------------------------------- cancelar_sessao


def test_cancelar_muda_o_status_e_devolve_a_sessao(agendamento, persistencia):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    cancelada = agendamento.cancelar_sessao(sessao.id)

    assert cancelada.id == sessao.id
    assert cancelada.status == StatusSessao.CANCELADA
    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.CANCELADA


def test_horario_volta_a_ficar_livre_depois_de_cancelar(agendamento):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    assert agendamento.verificar_disponibilidade(MENTOR_ID, DIA) == [H11]

    agendamento.cancelar_sessao(sessao.id)

    assert agendamento.verificar_disponibilidade(MENTOR_ID, DIA) == [H10, H11]


def test_cancelar_pede_notificacao_de_cancelamento(agendamento, espia):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)

    agendamento.cancelar_sessao(sessao.id)

    assert espia.cancelamentos == [(sessao.id, EMAIL_MENTOR, EMAIL_MENTORADO, H10)]


def test_cancelar_sessao_inexistente_levanta_erro(agendamento):
    with pytest.raises(SessaoNaoEncontrada):
        agendamento.cancelar_sessao("nao-existe")


def test_cancelar_duas_vezes_levanta_erro_e_avisa_so_uma_vez(agendamento, espia):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    agendamento.cancelar_sessao(sessao.id)

    with pytest.raises(CancelamentoNaoPermitido):
        agendamento.cancelar_sessao(sessao.id)
    assert len(espia.cancelamentos) == 1


def test_nao_cancela_sessao_que_ja_aconteceu(agendamento, persistencia, relogio):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    relogio.agora = datetime(2030, 1, 10, 10, 30)  # a sessão começou 30 min atrás

    with pytest.raises(CancelamentoNaoPermitido):
        agendamento.cancelar_sessao(sessao.id)

    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.MARCADA
    assert H10 not in agendamento.verificar_disponibilidade(MENTOR_ID, DIA)


def test_falha_no_aviso_nao_desfaz_o_cancelamento(agendamento, persistencia, espia, caplog):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    espia.erro = RuntimeError("notificações fora do ar")

    with caplog.at_level(logging.ERROR):
        cancelada = agendamento.cancelar_sessao(sessao.id)

    assert cancelada.status == StatusSessao.CANCELADA
    assert persistencia.buscar_sessao(sessao.id).status == StatusSessao.CANCELADA
    assert H10 in agendamento.verificar_disponibilidade(MENTOR_ID, DIA)


# ------------------------------------------------------------- relógio padrão do componente


def test_sem_relogio_informado_usa_a_hora_de_verdade(persistencia, espia):
    componente = ComponenteAgendamento(persistencia, espia)
    sessao = componente.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    # H10 é em 2030, então ainda não aconteceu e pode ser cancelada.
    assert componente.cancelar_sessao(sessao.id).status == StatusSessao.CANCELADA


def test_sem_dados_dos_usuarios_o_aviso_e_pulado_mas_a_sessao_fica(
    agendamento, persistencia, espia, monkeypatch, caplog
):
    sessao = agendamento.agendar_sessao(MENTOR_ID, MENTORADO_ID, H10)
    espia.cancelamentos.clear()
    monkeypatch.setattr(persistencia, "buscar_usuario", lambda _id: None)

    with caplog.at_level(logging.WARNING):
        cancelada = agendamento.cancelar_sessao(sessao.id)

    assert cancelada.status == StatusSessao.CANCELADA
    assert espia.cancelamentos == []
    assert "aviso não enviado" in caplog.text
