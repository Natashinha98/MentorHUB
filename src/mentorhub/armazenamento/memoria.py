"""Implementação em memória de IArmazenamentoImagens (apoio pros testes e pra demo)."""

from __future__ import annotations

from typing import Optional

from mentorhub.armazenamento.interfaces import FotoInvalida, IArmazenamentoImagens
from mentorhub.modelos import Foto

TAMANHO_MAXIMO = 1_000_000  # 1 MB


class ArmazenamentoEmMemoria(IArmazenamentoImagens):
    def __init__(self) -> None:
        self._fotos: dict[str, Foto] = {}

    def salvar_foto(self, usuario_id: str, foto: Foto) -> None:
        if not foto.tipo.startswith("image/"):
            raise FotoInvalida(f"Tipo de arquivo não aceito: {foto.tipo!r}.")
        if not foto.conteudo or len(foto.conteudo) > TAMANHO_MAXIMO:
            raise FotoInvalida("A foto precisa ter conteúdo e no máximo 1 MB.")
        self._fotos[usuario_id] = foto

    def recuperar_foto(self, usuario_id: str) -> Optional[Foto]:
        return self._fotos.get(usuario_id)
