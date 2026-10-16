"""Testes do armazenamento de imagens em memória (apoio da Busca de Mentores)."""

from __future__ import annotations

import pytest

from mentorhub.armazenamento.interfaces import FotoInvalida, IArmazenamentoImagens
from mentorhub.modelos import Foto


def test_implementa_a_interface(imagens):
    assert isinstance(imagens, IArmazenamentoImagens)


def test_salvar_e_recuperar(imagens):
    foto = Foto("image/png", b"bytes")
    imagens.salvar_foto("u1", foto)
    assert imagens.recuperar_foto("u1") == foto


def test_foto_nova_troca_a_anterior(imagens):
    imagens.salvar_foto("u1", Foto("image/png", b"antiga"))
    imagens.salvar_foto("u1", Foto("image/jpeg", b"nova"))
    assert imagens.recuperar_foto("u1") == Foto("image/jpeg", b"nova")


def test_usuario_sem_foto_devolve_none(imagens):
    assert imagens.recuperar_foto("ninguem") is None


@pytest.mark.parametrize(
    "foto",
    [Foto("text/html", b"<b>x</b>"), Foto("image/png", b""), Foto("image/png", b"x" * 1_000_001)],
)
def test_foto_invalida_e_recusada_e_nada_e_guardado(imagens, foto):
    with pytest.raises(FotoInvalida):
        imagens.salvar_foto("u1", foto)
    assert imagens.recuperar_foto("u1") is None
