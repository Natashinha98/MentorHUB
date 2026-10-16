"""Interface fornecida pelo componente de Busca de Mentores: IBuscaMentores.

As interfaces que o componente requer ficam com quem as fornece:
  - IPersistencia         -> mentorhub/persistencia/interfaces.py
  - IArmazenamentoImagens -> mentorhub/armazenamento/interfaces.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mentorhub.modelos import PerfilCompleto, ResumoMentor


class IBuscaMentores(ABC):
    """Procurar mentores e ver o perfil de cada um."""

    @abstractmethod
    def pesquisar_mentores(self, area: str) -> list[ResumoMentor]:
        """Lista os mentores que atendem numa área de conhecimento.

        Pré-condição:  a área não pode ser vazia (senão AreaInvalida).
        Saída:         mentores com alguma área que contenha o termo (sem diferenciar
                       maiúsculas e acentos), do mais bem avaliado pro menos, cada um
                       com nome, áreas, nota média e foto. Pode vir vazia.
        Pós-condição:  nada é alterado. Se a foto de um mentor não puder ser
                       carregada, ele aparece sem foto em vez de sumir da lista.
        """

    @abstractmethod
    def consultar_perfil(self, mentor_id: str) -> PerfilCompleto:
        """Mostra o perfil de um mentor com as avaliações que ele recebeu.

        Pré-condição:  o mentor existe e tem perfil (senão PerfilNaoEncontrado).
        Saída:         resumo, bio e avaliações do mentor.
        Pós-condição:  nada é alterado.
        """
