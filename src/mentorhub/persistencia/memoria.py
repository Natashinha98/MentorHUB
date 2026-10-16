"""Implementação em memória de IPersistencia (apoio pros testes e pra demo)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from threading import Lock
from typing import Optional

from mentorhub.modelos import Avaliacao, Conta, PerfilMentor, Sessao, Usuario
from mentorhub.persistencia.interfaces import IPersistencia
from mentorhub.textos import normalizar


class PersistenciaEmMemoria(IPersistencia):
    """Guarda tudo em dicionários. Os dados somem quando o programa termina."""

    def __init__(self) -> None:
        self._usuarios: dict[str, Usuario] = {}
        self._horarios_livres: dict[str, set[datetime]] = {}
        self._sessoes: dict[str, Sessao] = {}
        self._contas: dict[str, Conta] = {}  # por id do usuário
        self._perfis: dict[str, PerfilMentor] = {}
        self._avaliacoes: dict[str, list[Avaliacao]] = {}
        self._trava = Lock()

    # --- Métodos de apoio, só pra montar cenários (não fazem parte de IPersistencia) ---

    def salvar_usuario(self, usuario: Usuario) -> None:
        self._usuarios[usuario.id] = usuario

    def cadastrar_horario_livre(self, mentor_id: str, horario: datetime) -> None:
        with self._trava:
            self._horarios_livres.setdefault(mentor_id, set()).add(horario)

    # --- Operações de IPersistencia ---

    def buscar_usuario(self, usuario_id: str) -> Optional[Usuario]:
        return self._usuarios.get(usuario_id)

    def listar_horarios_livres(self, mentor_id: str, data: date) -> list[datetime]:
        with self._trava:
            livres = self._horarios_livres.get(mentor_id, set())
            return sorted(h for h in livres if h.date() == data)

    def ocupar_horario(self, mentor_id: str, horario: datetime) -> bool:
        with self._trava:
            livres = self._horarios_livres.get(mentor_id, set())
            if horario not in livres:
                return False
            livres.remove(horario)
            return True

    def liberar_horario(self, mentor_id: str, horario: datetime) -> None:
        with self._trava:
            self._horarios_livres.setdefault(mentor_id, set()).add(horario)

    def salvar_sessao(self, sessao: Sessao) -> None:
        # Guarda uma cópia, como um banco de verdade faria. Assim, mexer no objeto
        # depois de salvar não muda o que está guardado.
        self._sessoes[sessao.id] = replace(sessao)

    def buscar_sessao(self, sessao_id: str) -> Optional[Sessao]:
        sessao = self._sessoes.get(sessao_id)
        return replace(sessao) if sessao is not None else None

    # --- Contas ---

    def salvar_conta(self, conta: Conta) -> None:
        self._contas[conta.usuario.id] = conta
        self._usuarios[conta.usuario.id] = conta.usuario

    def buscar_conta_por_email(self, email: str) -> Optional[Conta]:
        procurado = email.strip().casefold()
        for conta in self._contas.values():
            if conta.usuario.email.strip().casefold() == procurado:
                return conta
        return None

    # --- Perfis e avaliações ---

    def salvar_perfil_mentor(self, perfil: PerfilMentor) -> None:
        self._perfis[perfil.mentor_id] = perfil

    def buscar_perfil_mentor(self, mentor_id: str) -> Optional[PerfilMentor]:
        return self._perfis.get(mentor_id)

    def listar_perfis_por_area(self, area: str) -> list[PerfilMentor]:
        termo = normalizar(area)
        return [
            perfil
            for perfil in self._perfis.values()
            if any(termo in normalizar(a) for a in perfil.areas)
        ]

    def salvar_avaliacao(self, avaliacao: Avaliacao) -> None:
        self._avaliacoes.setdefault(avaliacao.mentor_id, []).append(avaliacao)

    def listar_avaliacoes(self, mentor_id: str) -> list[Avaliacao]:
        return list(self._avaliacoes.get(mentor_id, []))
