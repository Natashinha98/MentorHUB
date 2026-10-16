"""Testes do componente de Busca de Mentores, isolado (persistência e imagens em memória)."""

from __future__ import annotations

import logging

import pytest

from mentorhub.armazenamento.interfaces import IArmazenamentoImagens
from mentorhub.busca.excecoes import AreaInvalida, ErroBusca, PerfilNaoEncontrado
from mentorhub.busca.interfaces import IBuscaMentores
from mentorhub.modelos import Foto, PerfilMentor


def test_implementa_a_interface_fornecida(busca):
    assert isinstance(busca, IBuscaMentores)
    with pytest.raises(TypeError):
        IBuscaMentores()


# --------------------------------------------------------------- pesquisar_mentores


def test_pesquisa_devolve_os_mentores_da_area(busca):
    resultado = busca.pesquisar_mentores("Python")
    assert {r.mentor_id for r in resultado} == {"m1", "m2"}


def test_resultado_vem_do_mais_bem_avaliado_pro_menos(busca):
    resultado = busca.pesquisar_mentores("Python")
    assert [r.nome for r in resultado] == ["Ana Mentora", "Carlos Mentor"]
    assert [r.nota_media for r in resultado] == [5.0, 4.0]


def test_pesquisa_ignora_maiusculas_acentos_e_aceita_parte_do_nome_da_area(busca):
    assert {r.mentor_id for r in busca.pesquisar_mentores("  pYTHON ")} == {"m1", "m2"}
    assert [r.mentor_id for r in busca.pesquisar_mentores("engenharia")] == ["m1"]
    assert [r.mentor_id for r in busca.pesquisar_mentores("CARREIRA")] == ["m3"]


def test_area_sem_mentores_devolve_lista_vazia(busca):
    assert busca.pesquisar_mentores("Culinária") == []


@pytest.mark.parametrize("area", ["", "   ", None])
def test_area_vazia_levanta_erro(busca, area):
    with pytest.raises(AreaInvalida):
        busca.pesquisar_mentores(area)


def test_resumo_traz_nome_areas_nota_total_e_foto(busca):
    ana = busca.pesquisar_mentores("Engenharia")[0]
    assert ana.nome == "Ana Mentora"
    assert ana.areas == ("Python", "Engenharia de Software")
    assert (ana.nota_media, ana.total_avaliacoes) == (5.0, 1)
    assert ana.foto == Foto("image/png", b"png-da-ana")


def test_mentor_sem_avaliacao_tem_nota_zero_e_sem_foto(busca):
    dora = busca.pesquisar_mentores("Carreira")[0]
    assert (dora.nota_media, dora.total_avaliacoes, dora.foto) == (0.0, 0, None)


def test_nota_media_e_arredondada_em_uma_casa(busca, banco):
    from mentorhub.modelos import Avaliacao

    banco.salvar_avaliacao(Avaliacao("m2", "a1", "Bruno", 5, "Ótimo."))
    banco.salvar_avaliacao(Avaliacao("m2", "a1", "Bruno", 5, "Ótimo de novo."))
    carlos = next(r for r in busca.pesquisar_mentores("Dados"))
    assert carlos.nota_media == 4.7  # (4 + 5 + 5) / 3
    assert carlos.total_avaliacoes == 3


def test_pesquisar_nao_altera_nada(busca, banco):
    antes = banco.listar_avaliacoes("m1"), banco.buscar_perfil_mentor("m1")
    busca.pesquisar_mentores("Python")
    assert (banco.listar_avaliacoes("m1"), banco.buscar_perfil_mentor("m1")) == antes


def test_falha_na_foto_nao_tira_o_mentor_da_lista(banco, imagens, busca, caplog):
    class ImagensComDefeito(IArmazenamentoImagens):
        def salvar_foto(self, usuario_id, foto):
            raise NotImplementedError

        def recuperar_foto(self, usuario_id):
            raise ConnectionError("armazenamento fora do ar")

    from mentorhub.busca.componente import ComponenteBuscaMentores

    componente = ComponenteBuscaMentores(banco, ImagensComDefeito())

    with caplog.at_level(logging.ERROR):
        resultado = componente.pesquisar_mentores("Python")

    assert [r.nome for r in resultado] == ["Ana Mentora", "Carlos Mentor"]
    assert all(r.foto is None for r in resultado)
    assert "Não foi possível carregar a foto" in caplog.text


def test_perfil_sem_usuario_correspondente_e_ignorado(busca, banco, caplog):
    banco.salvar_perfil_mentor(PerfilMentor("fantasma", ("Python",), "Sem usuário."))
    with caplog.at_level(logging.WARNING):
        resultado = busca.pesquisar_mentores("Python")
    assert "fantasma" not in {r.mentor_id for r in resultado}
    assert "sem usuário" in caplog.text


# ---------------------------------------------------------------- consultar_perfil


def test_perfil_traz_resumo_bio_e_avaliacoes(busca):
    perfil = busca.consultar_perfil("m1")

    assert perfil.resumo.nome == "Ana Mentora"
    assert perfil.resumo.foto is not None
    assert perfil.bio == "Bio de Ana Mentora."
    assert len(perfil.avaliacoes) == 1
    assert (perfil.avaliacoes[0].autor, perfil.avaliacoes[0].nota) == ("Bruno", 5)
    assert perfil.avaliacoes[0].comentario == "Ótima mentoria."


def test_perfil_de_mentor_sem_avaliacoes_vem_com_lista_vazia(busca):
    assert busca.consultar_perfil("m3").avaliacoes == ()


@pytest.mark.parametrize("mentor_id", ["nao-existe", "a1"])
def test_mentor_inexistente_ou_mentorado_levanta_erro(busca, mentor_id):
    with pytest.raises(PerfilNaoEncontrado):
        busca.consultar_perfil(mentor_id)


def test_erros_da_busca_tem_a_mesma_base():
    assert issubclass(AreaInvalida, ErroBusca) and issubclass(PerfilNaoEncontrado, ErroBusca)
