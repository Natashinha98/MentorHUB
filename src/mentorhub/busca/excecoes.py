"""Erros do componente de Busca de Mentores."""

from __future__ import annotations


class ErroBusca(Exception):
    """Base dos erros do componente de Busca de Mentores."""


class AreaInvalida(ErroBusca):
    """A área informada está vazia."""


class PerfilNaoEncontrado(ErroBusca):
    """O mentor não existe ou ainda não tem perfil."""
