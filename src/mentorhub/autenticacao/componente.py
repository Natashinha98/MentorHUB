"""Implementação do componente de Autenticação."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Callable
from uuid import uuid4

from mentorhub.autenticacao.excecoes import (
    CodigoRecuperacaoInvalido,
    ContaNaoEncontrada,
    CredenciaisInvalidas,
    DadosInvalidos,
)
from mentorhub.autenticacao.interfaces import IAutenticacao
from mentorhub.modelos import (
    CodigoRecuperacao,
    Conta,
    Papel,
    ResultadoValidacao,
    Usuario,
)
from mentorhub.persistencia.interfaces import IPersistencia

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PAPEIS_DE_CADASTRO = (Papel.MENTOR, Papel.MENTORADO)
VALIDADE_DO_CODIGO = timedelta(minutes=15)


class ComponenteAutenticacao(IAutenticacao):
    """Requer IPersistencia. O relógio, o gerador de IDs e as iterações do hash
    podem ser trocados no construtor, o que facilita os testes."""

    def __init__(
        self,
        persistencia: IPersistencia,
        agora: Callable[[], datetime] = datetime.now,
        gerar_id: Callable[[], str] = lambda: str(uuid4()),
        iteracoes_hash: int = 200_000,
    ) -> None:
        self._persistencia = persistencia
        self._agora = agora
        self._gerar_id = gerar_id
        self._iteracoes = iteracoes_hash

    # ------------------------------------------------------------------ operações

    def validar_cadastro(
        self, nome: str, email: str, senha: str, papel: Papel
    ) -> ResultadoValidacao:
        erros = list(self._erros_de_senha(senha))
        if not isinstance(nome, str) or len(nome.strip()) < 2:
            erros.insert(0, "O nome precisa ter pelo menos 2 letras.")
        if not isinstance(email, str) or not _EMAIL.match(email.strip()):
            erros.append("O e-mail não tem um formato válido.")
        elif self._persistencia.buscar_conta_por_email(email.strip()) is not None:
            erros.append("Já existe uma conta com esse e-mail.")
        if papel not in _PAPEIS_DE_CADASTRO:
            erros.append("O papel precisa ser mentor ou mentorado.")
        return ResultadoValidacao(valido=not erros, erros=tuple(erros))

    def criar_conta(self, nome: str, email: str, senha: str, papel: Papel) -> Usuario:
        resultado = self.validar_cadastro(nome, email, senha, papel)
        if not resultado.valido:
            raise DadosInvalidos(resultado.erros)
        usuario = Usuario(self._gerar_id(), nome.strip(), email.strip(), papel)
        salt = secrets.token_hex(16)
        self._persistencia.salvar_conta(Conta(usuario, salt, self._hash(senha, salt)))
        return usuario

    def autenticar_usuario(self, email: str, senha: str) -> Usuario:
        conta = self._persistencia.buscar_conta_por_email(email) if isinstance(email, str) else None
        if conta is None or not isinstance(senha, str):
            raise CredenciaisInvalidas()
        if not hmac.compare_digest(conta.senha_hash, self._hash(senha, conta.salt)):
            raise CredenciaisInvalidas()
        return conta.usuario

    def recuperar_acesso(self, email: str) -> CodigoRecuperacao:
        conta = self._persistencia.buscar_conta_por_email(email) if isinstance(email, str) else None
        if conta is None:
            raise ContaNaoEncontrada("Não existe conta com esse e-mail.")
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        expira_em = self._agora() + VALIDADE_DO_CODIGO
        self._persistencia.salvar_conta(
            replace(conta, codigo_hash=self._hash(codigo, conta.salt), codigo_expira_em=expira_em)
        )
        return CodigoRecuperacao(codigo, expira_em)

    def redefinir_senha(self, email: str, codigo: str, nova_senha: str) -> Usuario:
        conta = self._persistencia.buscar_conta_por_email(email) if isinstance(email, str) else None
        if conta is None or conta.codigo_hash is None or conta.codigo_expira_em is None:
            raise CodigoRecuperacaoInvalido("Não há recuperação de acesso em andamento.")
        if self._agora() > conta.codigo_expira_em:
            raise CodigoRecuperacaoInvalido("O código venceu. Peça um novo.")
        if not isinstance(codigo, str) or not hmac.compare_digest(
            conta.codigo_hash, self._hash(codigo.strip(), conta.salt)
        ):
            raise CodigoRecuperacaoInvalido("Código incorreto.")
        erros = self._erros_de_senha(nova_senha)
        if erros:
            raise DadosInvalidos(erros)
        novo_salt = secrets.token_hex(16)
        self._persistencia.salvar_conta(
            Conta(conta.usuario, novo_salt, self._hash(nova_senha, novo_salt))
        )
        return conta.usuario

    # ------------------------------------------------------------------- apoio

    def _hash(self, texto: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", texto.encode("utf-8"), bytes.fromhex(salt), self._iteracoes
        ).hex()

    @staticmethod
    def _erros_de_senha(senha: str) -> tuple[str, ...]:
        if not isinstance(senha, str):
            return ("A senha precisa ser um texto.",)
        erros = []
        if len(senha) < 8:
            erros.append("A senha precisa ter pelo menos 8 caracteres.")
        if not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
            erros.append("A senha precisa ter letras e números.")
        return tuple(erros)
