"""Pequenas funções de texto usadas por mais de um módulo (não é um componente)."""

from __future__ import annotations

import unicodedata


def normalizar(texto: str) -> str:
    """Deixa o texto sem acento, minúsculo e sem espaços nas pontas, pra comparar."""
    sem_acento = unicodedata.normalize("NFD", texto.strip())
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return sem_acento.casefold()
