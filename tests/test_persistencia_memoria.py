"""Testes da persistência em memória (apoio). Garantem que o stand-in se comporta
como a interface IPersistencia promete, já que os outros testes dependem dele."""

from __future__ import annotations

from apoio import DIA, H10, H11, MENTOR_ID, OUTRO_DIA_H9

from mentorhub.modelos import Sessao, StatusSessao
from mentorhub.persistencia.interfaces import IPersistencia


def test_implementa_a_interface(persistencia):
    assert isinstance(persistencia, IPersistencia)


def test_buscar_usuario_inexistente_devolve_none(persistencia):
    assert persistencia.buscar_usuario("nao-existe") is None


def test_listar_filtra_por_data_e_ordena(persistencia):
    assert persistencia.listar_horarios_livres(MENTOR_ID, DIA) == [H10, H11]
    assert persistencia.listar_horarios_livres(MENTOR_ID, OUTRO_DIA_H9.date()) == [OUTRO_DIA_H9]


def test_ocupar_horario_so_funciona_uma_vez(persistencia):
    assert persistencia.ocupar_horario(MENTOR_ID, H10) is True
    assert persistencia.ocupar_horario(MENTOR_ID, H10) is False
    assert H10 not in persistencia.listar_horarios_livres(MENTOR_ID, DIA)


def test_liberar_horario_devolve_pra_lista(persistencia):
    persistencia.ocupar_horario(MENTOR_ID, H10)
    persistencia.liberar_horario(MENTOR_ID, H10)
    assert H10 in persistencia.listar_horarios_livres(MENTOR_ID, DIA)


def test_salvar_sessao_guarda_uma_copia(persistencia):
    sessao = Sessao("s1", MENTOR_ID, "a1", H10)
    persistencia.salvar_sessao(sessao)

    sessao.status = StatusSessao.CANCELADA  # mexe no objeto original, sem salvar

    assert persistencia.buscar_sessao("s1").status == StatusSessao.MARCADA
    assert persistencia.buscar_sessao("nao-existe") is None


# ---------------------------------------------------- contas, perfis e avaliações

from dataclasses import replace  # noqa: E402

from mentorhub.modelos import Avaliacao, Conta, Papel, PerfilMentor, Usuario  # noqa: E402


def conta_de(usuario_id="u1", email="Ana@MentorHub.com"):
    return Conta(Usuario(usuario_id, "Ana", email, Papel.MENTOR), salt="aa", senha_hash="bb")


def test_salvar_conta_tambem_deixa_o_usuario_disponivel(persistencia):
    conta = conta_de()
    persistencia.salvar_conta(conta)
    assert persistencia.buscar_usuario("u1") == conta.usuario


def test_buscar_conta_por_email_ignora_maiusculas_e_espacos(persistencia):
    persistencia.salvar_conta(conta_de())
    assert persistencia.buscar_conta_por_email("  ana@mentorhub.COM ").usuario.id == "u1"
    assert persistencia.buscar_conta_por_email("outro@mentorhub.com") is None


def test_salvar_conta_de_novo_atualiza(persistencia):
    persistencia.salvar_conta(conta_de())
    persistencia.salvar_conta(replace(conta_de(), senha_hash="novo"))
    assert persistencia.buscar_conta_por_email("ana@mentorhub.com").senha_hash == "novo"


def test_perfis_filtrados_por_area_sem_acento_nem_maiuscula(persistencia):
    persistencia.salvar_perfil_mentor(PerfilMentor("m1", ("Programação", "Dados"), "bio"))
    persistencia.salvar_perfil_mentor(PerfilMentor("m2", ("Carreira",), "bio"))

    assert [p.mentor_id for p in persistencia.listar_perfis_por_area("PROGRAMACAO")] == ["m1"]
    assert [p.mentor_id for p in persistencia.listar_perfis_por_area("carr")] == ["m2"]
    assert persistencia.listar_perfis_por_area("culinária") == []
    assert persistencia.buscar_perfil_mentor("m2").areas == ("Carreira",)
    assert persistencia.buscar_perfil_mentor("nao-existe") is None


def test_avaliacoes_ficam_na_ordem_em_que_foram_salvas(persistencia):
    primeira = Avaliacao("m1", "a1", "Bruno", 5, "ótimo")
    segunda = Avaliacao("m1", "a2", "Carla", 3, "ok")
    persistencia.salvar_avaliacao(primeira)
    persistencia.salvar_avaliacao(segunda)
    assert persistencia.listar_avaliacoes("m1") == [primeira, segunda]
    assert persistencia.listar_avaliacoes("m2") == []
