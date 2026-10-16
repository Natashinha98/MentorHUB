"""Modelos de dados compartilhados entre os componentes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Papel(str, Enum):
    """Papel de um usuário no MentorHub."""

    MENTOR = "mentor"
    MENTORADO = "mentorado"
    ADMINISTRADOR = "administrador"


class StatusSessao(str, Enum):
    """Situação de uma sessão de mentoria."""

    MARCADA = "marcada"
    CANCELADA = "cancelada"


@dataclass(frozen=True)
class Usuario:
    """Usuário do sistema (mentor, mentorado ou administrador)."""

    id: str
    nome: str
    email: str
    papel: Papel


@dataclass
class Sessao:
    """Sessão de mentoria marcada entre um mentor e um mentorado."""

    id: str
    mentor_id: str
    mentorado_id: str
    horario: datetime
    status: StatusSessao = StatusSessao.MARCADA


@dataclass(frozen=True)
class ResultadoEnvio:
    """Resultado de um pedido de notificação.

    enviado=True só quando a mensagem chegou a todos os destinatários.
    Em caso de falha, `falhas` diz quem não recebeu e por quê.
    """

    enviado: bool
    falhas: tuple[str, ...] = ()


# --------------------------------------------------------------- Autenticação


@dataclass(frozen=True)
class Conta:
    """Conta de acesso de um usuário. A senha nunca é guardada, só o hash com sal.

    `codigo_hash` e `codigo_expira_em` só existem enquanto há uma recuperação de
    acesso em andamento.
    """

    usuario: Usuario
    salt: str
    senha_hash: str
    codigo_hash: Optional[str] = None
    codigo_expira_em: Optional[datetime] = None


@dataclass(frozen=True)
class ResultadoValidacao:
    """Resultado de `validar_cadastro`: valido=True só quando `erros` está vazio."""

    valido: bool
    erros: tuple[str, ...] = ()


@dataclass(frozen=True)
class CodigoRecuperacao:
    """Código de uso único pra redefinir a senha, com prazo de validade."""

    codigo: str
    expira_em: datetime


# ------------------------------------------------------------ Busca de mentores


@dataclass(frozen=True)
class Foto:
    """Foto de perfil: tipo (por exemplo image/png) e o conteúdo em bytes."""

    tipo: str
    conteudo: bytes


@dataclass(frozen=True)
class PerfilMentor:
    """Dados do perfil de um mentor, como ficam guardados."""

    mentor_id: str
    areas: tuple[str, ...]
    bio: str


@dataclass(frozen=True)
class Avaliacao:
    """Avaliação que um mentorado deu a um mentor (nota de 1 a 5)."""

    mentor_id: str
    mentorado_id: str
    autor: str
    nota: int
    comentario: str


@dataclass(frozen=True)
class ResumoMentor:
    """Item da lista de resultados da busca."""

    mentor_id: str
    nome: str
    areas: tuple[str, ...]
    nota_media: float
    total_avaliacoes: int
    foto: Optional[Foto] = None


@dataclass(frozen=True)
class PerfilCompleto:
    """Perfil de um mentor com as avaliações recebidas."""

    resumo: ResumoMentor
    bio: str
    avaliacoes: tuple[Avaliacao, ...]
