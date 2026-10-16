"""Implementação do componente de Busca de Mentores."""

from __future__ import annotations

import logging
from typing import Optional

from mentorhub.armazenamento.interfaces import IArmazenamentoImagens
from mentorhub.busca.excecoes import AreaInvalida, PerfilNaoEncontrado
from mentorhub.busca.interfaces import IBuscaMentores
from mentorhub.modelos import Avaliacao, Foto, PerfilCompleto, PerfilMentor, ResumoMentor
from mentorhub.persistencia.interfaces import IPersistencia

logger = logging.getLogger(__name__)


class ComponenteBuscaMentores(IBuscaMentores):
    """Requer IPersistencia (perfis, avaliações, nomes) e IArmazenamentoImagens (fotos)."""

    def __init__(self, persistencia: IPersistencia, imagens: IArmazenamentoImagens) -> None:
        self._persistencia = persistencia
        self._imagens = imagens

    def pesquisar_mentores(self, area: str) -> list[ResumoMentor]:
        if not isinstance(area, str) or not area.strip():
            raise AreaInvalida("Informe uma área de conhecimento.")
        resumos = []
        for perfil in self._persistencia.listar_perfis_por_area(area.strip()):
            resumo = self._resumir(perfil, self._persistencia.listar_avaliacoes(perfil.mentor_id))
            if resumo is not None:
                resumos.append(resumo)
        return sorted(resumos, key=lambda r: (-r.nota_media, r.nome.casefold()))

    def consultar_perfil(self, mentor_id: str) -> PerfilCompleto:
        perfil = self._persistencia.buscar_perfil_mentor(mentor_id)
        avaliacoes = self._persistencia.listar_avaliacoes(mentor_id)
        resumo = self._resumir(perfil, avaliacoes) if perfil is not None else None
        if resumo is None:
            raise PerfilNaoEncontrado(f"O mentor {mentor_id} não existe ou não tem perfil.")
        return PerfilCompleto(resumo, perfil.bio, tuple(avaliacoes))

    # ------------------------------------------------------------------- apoio

    def _resumir(self, perfil: PerfilMentor, avaliacoes: list[Avaliacao]) -> Optional[ResumoMentor]:
        mentor = self._persistencia.buscar_usuario(perfil.mentor_id)
        if mentor is None:
            logger.warning("Perfil %s sem usuário correspondente; ignorado.", perfil.mentor_id)
            return None
        total = len(avaliacoes)
        media = round(sum(a.nota for a in avaliacoes) / total, 1) if total else 0.0
        return ResumoMentor(
            mentor_id=mentor.id,
            nome=mentor.nome,
            areas=perfil.areas,
            nota_media=media,
            total_avaliacoes=total,
            foto=self._foto_de(mentor.id),
        )

    def _foto_de(self, mentor_id: str) -> Optional[Foto]:
        try:
            return self._imagens.recuperar_foto(mentor_id)
        except Exception:  # sem foto, o mentor continua aparecendo
            logger.exception("Não foi possível carregar a foto do mentor %s.", mentor_id)
            return None
