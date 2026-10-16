"""Interface IArmazenamentoImagens, requerida pelo componente de Busca de Mentores.

Na arquitetura, quem fornece essa interface é o Componente de Armazenamento de
Perfil (Supabase Storage). Ele não está entre os componentes implementados neste
laboratório, então existe só a interface e, em armazenamento/memoria.py, uma
implementação em memória de apoio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from mentorhub.modelos import Foto


class IArmazenamentoImagens(ABC):
    """Operações de foto de perfil."""

    @abstractmethod
    def salvar_foto(self, usuario_id: str, foto: Foto) -> None:
        """Guarda a foto de perfil do usuário, trocando a anterior se houver.

        Pré-condição: o tipo precisa ser de imagem (image/...) e o conteúdo não
        pode ser vazio nem passar de 1 MB (senão FotoInvalida).
        """

    @abstractmethod
    def recuperar_foto(self, usuario_id: str) -> Optional[Foto]:
        """Devolve a foto de perfil do usuário, ou None se ele não tiver foto."""


class FotoInvalida(ValueError):
    """A foto não respeita o tipo ou o tamanho aceitos."""
