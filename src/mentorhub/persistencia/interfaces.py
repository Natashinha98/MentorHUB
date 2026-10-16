"""Interface IPersistencia, requerida pelos componentes de Agendamento, Autenticação
e Busca de Mentores.

Na arquitetura, quem fornece essa interface é o Componente de Persistência de
Dados (Supabase/PostgreSQL). Esse componente não está entre os dois escolhidos
pro laboratório, então aqui existe só a interface e, em persistencia/memoria.py,
uma implementação em memória que serve de apoio pros testes e pra demo.
Se um dia o banco real entrar, basta uma classe nova que implemente esta interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from mentorhub.modelos import Avaliacao, Conta, PerfilMentor, Sessao, Usuario


class IPersistencia(ABC):
    """Operações de persistência de que os componentes precisam."""

    @abstractmethod
    def buscar_usuario(self, usuario_id: str) -> Optional[Usuario]:
        """Devolve o usuário com esse ID, ou None se não existir."""

    @abstractmethod
    def listar_horarios_livres(self, mentor_id: str, data: date) -> list[datetime]:
        """Devolve, em ordem, os horários livres do mentor naquela data."""

    @abstractmethod
    def ocupar_horario(self, mentor_id: str, horario: datetime) -> bool:
        """Tira o horário da lista de livres do mentor.

        Devolve True se o horário estava livre e foi ocupado, e False se não
        estava livre. A checagem e a reserva acontecem juntas, pra dois
        agendamentos não pegarem o mesmo horário.
        """

    @abstractmethod
    def liberar_horario(self, mentor_id: str, horario: datetime) -> None:
        """Devolve o horário pra lista de livres do mentor."""

    @abstractmethod
    def salvar_sessao(self, sessao: Sessao) -> None:
        """Salva a sessão (cria se for nova, atualiza se já existir)."""

    @abstractmethod
    def buscar_sessao(self, sessao_id: str) -> Optional[Sessao]:
        """Devolve a sessão com esse ID, ou None se não existir."""

    # ---- Contas (usadas pela Autenticação) ----

    @abstractmethod
    def salvar_conta(self, conta: Conta) -> None:
        """Salva a conta (e o usuário dela). Cria se for nova, atualiza se já existir."""

    @abstractmethod
    def buscar_conta_por_email(self, email: str) -> Optional[Conta]:
        """Devolve a conta com esse e-mail (sem diferenciar maiúsculas), ou None."""

    # ---- Perfis e avaliações (usados pela Busca de Mentores) ----

    @abstractmethod
    def salvar_perfil_mentor(self, perfil: PerfilMentor) -> None:
        """Salva o perfil do mentor (cria ou atualiza)."""

    @abstractmethod
    def buscar_perfil_mentor(self, mentor_id: str) -> Optional[PerfilMentor]:
        """Devolve o perfil do mentor, ou None se ele não tiver perfil."""

    @abstractmethod
    def listar_perfis_por_area(self, area: str) -> list[PerfilMentor]:
        """Devolve os perfis com alguma área que contenha o termo.

        A comparação ignora maiúsculas, minúsculas e acentos.
        """

    @abstractmethod
    def salvar_avaliacao(self, avaliacao: Avaliacao) -> None:
        """Guarda uma avaliação recebida por um mentor."""

    @abstractmethod
    def listar_avaliacoes(self, mentor_id: str) -> list[Avaliacao]:
        """Devolve as avaliações do mentor, da mais antiga pra mais recente."""
