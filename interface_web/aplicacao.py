"""Camada de aplicação da interface web: Autenticação e Busca de Mentores.

Monta os componentes reais sobre a persistência e o armazenamento de imagens em
memória, com contas e mentores de teste. A sessão de login (quem está logado) fica
aqui, na camada da interface: os componentes não têm esse conceito.
"""

from __future__ import annotations

import base64
import threading
from xml.sax.saxutils import escape

from mentorhub.armazenamento.memoria import ArmazenamentoEmMemoria
from mentorhub.autenticacao.componente import ComponenteAutenticacao
from mentorhub.autenticacao.excecoes import DadosInvalidos, ErroAutenticacao
from mentorhub.busca.componente import ComponenteBuscaMentores
from mentorhub.busca.excecoes import ErroBusca
from mentorhub.modelos import Avaliacao, Foto, Papel, PerfilMentor, ResumoMentor, Usuario
from mentorhub.persistencia.memoria import PersistenciaEmMemoria

SENHA_DAS_CONTAS_DE_TESTE = "senha1234"
AREAS_SUGERIDAS = ["Python", "Dados", "Carreira", "Engenharia de Software"]

# (id, nome, e-mail, papel, áreas, bio)
MENTORES = [
    ("m1", "Ana Mentora", "ana@mentorhub.com", ("Python", "Engenharia de Software"),
     "Engenheira de software há 9 anos. Ajuda quem está começando em Python e quer evoluir em arquitetura e boas práticas."),
    ("m2", "Carlos Mentor", "carlos@mentorhub.com", ("Dados", "Python"),
     "Cientista de dados. Mentoria de análise de dados, SQL e primeiros modelos de machine learning."),
    ("m3", "Dora Mentora", "dora@mentorhub.com", ("Carreira", "Engenharia de Software"),
     "Tech lead. Conversa sobre transição de carreira, entrevistas técnicas e liderança."),
]
MENTORADOS = [
    ("a1", "Bruno Mentorado", "bruno@mentorhub.com"),
    ("a2", "Carla Mentorada", "carla@mentorhub.com"),
]
# (mentor, autor, nota, comentário)
AVALIACOES = [
    ("m1", "a1", "Bruno", 5, "Explicou tudo com calma e me deu um plano de estudos."),
    ("m1", "a2", "Carla", 5, "Ótimas dicas de arquitetura. Recomendo."),
    ("m1", "a1", "Bruno", 4, "Muito boa, só faltou um pouco mais de exemplos práticos."),
    ("m2", "a2", "Carla", 4, "Me ajudou a organizar a análise do meu projeto."),
    ("m2", "a1", "Bruno", 5, "Didático e paciente."),
]
CORES_AVATAR = ["#4f46e5", "#0d9488", "#d97706", "#db2777", "#7c3aed", "#0369a1"]

class NaoAutenticado(Exception):
    """Ninguém está logado."""


def avatar_svg(nome: str) -> bytes:
    """Foto de perfil de mentirinha: um círculo colorido com as iniciais."""
    iniciais = "".join(p[0] for p in nome.split()[:2]).upper() or "?"
    cor = CORES_AVATAR[sum(map(ord, nome)) % len(CORES_AVATAR)]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">'
        f'<rect width="96" height="96" fill="{cor}"/>'
        '<text x="48" y="60" font-family="Arial,sans-serif" font-size="38" font-weight="700" '
        f'fill="#fff" text-anchor="middle">{escape(iniciais)}</text></svg>'
    )
    return svg.encode("utf-8")


def avatar_svg(nome: str) -> bytes:
    """Foto de perfil de mentirinha: um círculo colorido com as iniciais."""
    iniciais = "".join(p[0] for p in nome.split()[:2]).upper() or "?"
    cor = CORES_AVATAR[sum(map(ord, nome)) % len(CORES_AVATAR)]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">'
        f'<rect width="96" height="96" fill="{cor}"/>'
        '<text x="48" y="60" font-family="Arial,sans-serif" font-size="38" font-weight="700" '
        f'fill="#fff" text-anchor="middle">{escape(iniciais)}</text></svg>'
    )
    return svg.encode("utf-8")


def _foto_para_json(foto: Foto | None) -> str | None:
    if foto is None:
        return None
    return f"data:{foto.tipo};base64,{base64.b64encode(foto.conteudo).decode()}"


def _resumo_json(r: ResumoMentor) -> dict:
    return {
        "id": r.mentor_id, "nome": r.nome, "areas": list(r.areas), "nota": r.nota_media,
        "total": r.total_avaliacoes, "foto": _foto_para_json(r.foto),
    }



class Demo:
    """Estado da demonstração. Uma instância = um 'banco' zerado."""

    def __init__(self, iteracoes_hash: int = 100_000) -> None:
        self._iteracoes = iteracoes_hash
        self._trava = threading.RLock()
        self.reiniciar()

    def reiniciar(self) -> None:
        with self._trava:
            self.usuario: Usuario | None = None
            self.banco = PersistenciaEmMemoria()
            self.imagens_banco = ArmazenamentoEmMemoria()
            self._popular()
            self.autenticacao = ComponenteAutenticacao(self.banco, iteracoes_hash=self._iteracoes)
            self.busca = ComponenteBuscaMentores(self.banco, self.imagens_banco)

    def _popular(self) -> None:
        """Cadastra as contas e perfis de teste."""
        for usuario_id, nome, email, areas, bio in MENTORES:
            self._semear_conta(usuario_id, nome, email, Papel.MENTOR)
            self.banco.salvar_perfil_mentor(PerfilMentor(usuario_id, areas, bio))
        for usuario_id, nome, email in MENTORADOS:
            self._semear_conta(usuario_id, nome, email, Papel.MENTORADO)
        for mentor_id, mentorado_id, autor, nota, comentario in AVALIACOES:
            self.banco.salvar_avaliacao(Avaliacao(mentor_id, mentorado_id, autor, nota, comentario))

    def _semear_conta(self, usuario_id: str, nome: str, email: str, papel: Papel) -> None:
        semeador = ComponenteAutenticacao(
            self.banco, gerar_id=lambda: usuario_id, iteracoes_hash=self._iteracoes
        )
        semeador.criar_conta(nome, email, SENHA_DAS_CONTAS_DE_TESTE, papel)
        self.imagens_banco.salvar_foto(usuario_id, Foto("image/svg+xml", avatar_svg(nome)))

    # ---------------------------------------------------------- conta e acesso

    def entrar(self, email: str, senha: str) -> dict:
        with self._trava:
            try:
                self.usuario = self.autenticacao.autenticar_usuario(email, senha)
            except ErroAutenticacao as erro:
                return self._resposta(erro=erro)
            return self._resposta(mensagem=f"Bem-vindo(a), {self.usuario.nome}.")

    def sair(self) -> dict:
        with self._trava:
            self.usuario = None
            return self._resposta(mensagem="Você saiu da conta.")

    def cadastrar(self, nome, email, senha, papel, area=None, bio=None) -> dict:
        """Valida e cria a conta (validar_cadastro e depois criar_conta)."""
        with self._trava:
            try:
                papel_enum = Papel(papel)
            except ValueError:
                papel_enum = None
            try:
                validacao = self.autenticacao.validar_cadastro(nome, email, senha, papel_enum)
                if not validacao.valido:
                    raise DadosInvalidos(validacao.erros)
                usuario = self.autenticacao.criar_conta(nome, email, senha, papel_enum)
            except ErroAutenticacao as erro:
                return self._resposta(erro=erro)
            self._completar_cadastro(usuario, area, bio)
            return self._resposta(mensagem="Conta criada. Agora é só entrar.", dados={"email": usuario.email})

    def _completar_cadastro(self, usuario: Usuario, area: str | None, bio: str | None) -> None:
        """Apoio da demo: foto padrão e, se for mentor, o perfil. Não é operação da Autenticação."""
        self.imagens_banco.salvar_foto(usuario.id, Foto("image/svg+xml", avatar_svg(usuario.nome)))
        if usuario.papel == Papel.MENTOR:
            areas = tuple(a.strip() for a in (area or "").split(",") if a.strip()) or ("Geral",)
            self.banco.salvar_perfil_mentor(
                PerfilMentor(usuario.id, areas, (bio or "").strip() or "Mentor recém-chegado ao MentorHub.")
            )

    def recuperar_acesso(self, email: str) -> dict:
        with self._trava:
            try:
                codigo = self.autenticacao.recuperar_acesso(email)
            except ErroAutenticacao as erro:
                return self._resposta(erro=erro)
            return self._resposta(
                mensagem="Código gerado.",
                dados={"codigo": codigo.codigo, "expira_em": codigo.expira_em.strftime("%H:%M")},
            )

    def redefinir_senha(self, email: str, codigo: str, nova_senha: str) -> dict:
        with self._trava:
            try:
                self.autenticacao.redefinir_senha(email, codigo, nova_senha)
            except ErroAutenticacao as erro:
                return self._resposta(erro=erro)
            return self._resposta(mensagem="Senha alterada. Entre com a senha nova.")

    # -------------------------------------------------------------------- busca

    def pesquisar(self, area: str) -> dict:
        with self._trava:
            try:
                self._exigir_login()
                resultados = self.busca.pesquisar_mentores(area)
            except (ErroBusca, NaoAutenticado) as erro:
                return self._resposta(erro=erro)
            return self._resposta(dados={"resultados": [_resumo_json(r) for r in resultados]})

    def perfil(self, perfil_id: str) -> dict:
        with self._trava:
            try:
                self._exigir_login()
                perfil = self.busca.consultar_perfil(perfil_id)
            except (ErroBusca, NaoAutenticado) as erro:
                return self._resposta(erro=erro)
            return self._resposta(dados={"perfil": {
                **_resumo_json(perfil.resumo), "bio": perfil.bio,
                "avaliacoes": [
                    {"autor": a.autor, "nota": a.nota, "comentario": a.comentario} for a in perfil.avaliacoes
                ],
            }})

    # -------------------------------------------------------------------- estado

    def _exigir_login(self) -> None:
        if self.usuario is None:
            raise NaoAutenticado("Entre na sua conta para continuar.")

    def _resposta(self, mensagem=None, erro: Exception | None = None, dados=None) -> dict:
        info = None
        if erro is not None:
            info = {"tipo": type(erro).__name__, "mensagem": str(erro),
                    "detalhes": list(erro.erros) if isinstance(erro, DadosInvalidos) else []}
        return {"ok": erro is None, "mensagem": mensagem, "erro": info, "dados": dados, "estado": self.estado()}

    def estado(self) -> dict:
        with self._trava:
            return {
                "usuario": None if self.usuario is None else {
                    "id": self.usuario.id, "nome": self.usuario.nome,
                    "email": self.usuario.email, "papel": self.usuario.papel.value,
                },
                "contas_teste": [
                    {"nome": n, "email": e, "senha": SENHA_DAS_CONTAS_DE_TESTE, "papel": "mentor"}
                    for _, n, e, _, _ in MENTORES[:1]
                ] + [
                    {"nome": n, "email": e, "senha": SENHA_DAS_CONTAS_DE_TESTE, "papel": "mentorado"}
                    for _, n, e in MENTORADOS
                ],
                "areas_sugeridas": AREAS_SUGERIDAS,
            }
