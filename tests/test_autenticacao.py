"""Testes do componente de Autenticação, isolado (a persistência é a de memória)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from mentorhub.autenticacao.excecoes import (
    CodigoRecuperacaoInvalido,
    ContaNaoEncontrada,
    CredenciaisInvalidas,
    DadosInvalidos,
    ErroAutenticacao,
)
from mentorhub.autenticacao.interfaces import IAutenticacao
from mentorhub.modelos import Papel

EMAIL = "bruno@mentorhub.com"
SENHA = "senha1234"


@pytest.fixture
def bruno(autenticacao):
    return autenticacao.criar_conta("Bruno Mentorado", EMAIL, SENHA, Papel.MENTORADO)


def test_implementa_a_interface_fornecida(autenticacao):
    assert isinstance(autenticacao, IAutenticacao)
    with pytest.raises(TypeError):
        IAutenticacao()


# ----------------------------------------------------------------- validar_cadastro


def test_dados_corretos_sao_validos(autenticacao):
    resultado = autenticacao.validar_cadastro("Bruno", EMAIL, SENHA, Papel.MENTORADO)
    assert resultado.valido is True and resultado.erros == ()


@pytest.mark.parametrize(
    "nome, email, senha, papel, trecho",
    [
        ("B", EMAIL, SENHA, Papel.MENTORADO, "nome"),
        ("   ", EMAIL, SENHA, Papel.MENTORADO, "nome"),
        ("Bruno", "sem-arroba", SENHA, Papel.MENTORADO, "e-mail"),
        ("Bruno", "a@b", SENHA, Papel.MENTORADO, "e-mail"),
        ("Bruno", EMAIL, "curta1", Papel.MENTORADO, "8 caracteres"),
        ("Bruno", EMAIL, "somenteletras", Papel.MENTORADO, "letras e números"),
        ("Bruno", EMAIL, "123456789", Papel.MENTORADO, "letras e números"),
        ("Bruno", EMAIL, SENHA, Papel.ADMINISTRADOR, "papel"),
    ],
)
def test_cada_regra_violada_aparece_nos_erros(autenticacao, nome, email, senha, papel, trecho):
    resultado = autenticacao.validar_cadastro(nome, email, senha, papel)
    assert resultado.valido is False
    assert any(trecho in erro for erro in resultado.erros)


def test_varios_erros_sao_devolvidos_de_uma_vez(autenticacao):
    resultado = autenticacao.validar_cadastro("", "x", "1", Papel.MENTORADO)
    assert len(resultado.erros) >= 4


def test_email_ja_cadastrado_e_recusado_sem_diferenciar_maiusculas(autenticacao, bruno):
    resultado = autenticacao.validar_cadastro("Outro", EMAIL.upper(), SENHA, Papel.MENTOR)
    assert resultado.valido is False
    assert any("Já existe uma conta" in erro for erro in resultado.erros)


def test_validar_nao_cria_conta(autenticacao, banco):
    autenticacao.validar_cadastro("Bruno", EMAIL, SENHA, Papel.MENTORADO)
    assert banco.buscar_conta_por_email(EMAIL) is None


# -------------------------------------------------------------------- criar_conta


def test_criar_conta_devolve_o_usuario_e_salva(autenticacao, banco, bruno):
    assert (bruno.nome, bruno.email, bruno.papel) == ("Bruno Mentorado", EMAIL, Papel.MENTORADO)
    assert banco.buscar_usuario(bruno.id) == bruno
    assert banco.buscar_conta_por_email(EMAIL).usuario == bruno


def test_a_senha_nao_fica_guardada_em_texto(banco, bruno):
    conta = banco.buscar_conta_por_email(EMAIL)
    assert SENHA not in (conta.senha_hash, conta.salt)
    assert len(conta.senha_hash) == 64


def test_duas_contas_com_a_mesma_senha_tem_hashes_diferentes(autenticacao, banco, bruno):
    autenticacao.criar_conta("Carla", "carla@mentorhub.com", SENHA, Papel.MENTORADO)
    assert (
        banco.buscar_conta_por_email(EMAIL).senha_hash
        != banco.buscar_conta_por_email("carla@mentorhub.com").senha_hash
    )


def test_criar_conta_com_dados_invalidos_levanta_erro_e_nao_salva(autenticacao, banco):
    with pytest.raises(DadosInvalidos) as erro:
        autenticacao.criar_conta("Bruno", "sem-arroba", "curta", Papel.MENTORADO)
    assert len(erro.value.erros) >= 2
    assert banco.buscar_conta_por_email("sem-arroba") is None


def test_nao_cria_duas_contas_com_o_mesmo_email(autenticacao, bruno):
    with pytest.raises(DadosInvalidos):
        autenticacao.criar_conta("Outro Bruno", EMAIL, SENHA, Papel.MENTOR)


def test_todos_os_erros_tem_a_mesma_base():
    for erro in (DadosInvalidos, CredenciaisInvalidas, ContaNaoEncontrada, CodigoRecuperacaoInvalido):
        assert issubclass(erro, ErroAutenticacao)


# ------------------------------------------------------------- autenticar_usuario


def test_login_correto_devolve_o_usuario(autenticacao, bruno):
    assert autenticacao.autenticar_usuario(EMAIL, SENHA) == bruno


def test_login_ignora_maiusculas_e_espacos_no_email(autenticacao, bruno):
    assert autenticacao.autenticar_usuario("  Bruno@MentorHub.com ", SENHA) == bruno


def test_senha_errada_e_email_inexistente_dao_a_mesma_mensagem(autenticacao, bruno):
    with pytest.raises(CredenciaisInvalidas) as senha_errada:
        autenticacao.autenticar_usuario(EMAIL, "senhaerrada1")
    with pytest.raises(CredenciaisInvalidas) as sem_conta:
        autenticacao.autenticar_usuario("ninguem@mentorhub.com", SENHA)
    assert str(senha_errada.value) == str(sem_conta.value)


def test_senha_diferenciando_maiusculas(autenticacao, bruno):
    with pytest.raises(CredenciaisInvalidas):
        autenticacao.autenticar_usuario(EMAIL, SENHA.upper())


# ------------------------------------------------- recuperar_acesso e redefinir_senha


def test_recuperar_acesso_devolve_codigo_de_6_digitos_com_prazo(autenticacao, agora_auth, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    assert len(codigo.codigo) == 6 and codigo.codigo.isdigit()
    assert codigo.expira_em == agora_auth.agora + timedelta(minutes=15)


def test_so_o_hash_do_codigo_fica_guardado(banco, autenticacao, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    conta = banco.buscar_conta_por_email(EMAIL)
    assert conta.codigo_hash and codigo.codigo not in conta.codigo_hash


def test_recuperar_acesso_de_email_sem_conta_levanta_erro(autenticacao):
    with pytest.raises(ContaNaoEncontrada):
        autenticacao.recuperar_acesso("ninguem@mentorhub.com")


def test_redefinir_senha_troca_a_senha(autenticacao, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)

    usuario = autenticacao.redefinir_senha(EMAIL, codigo.codigo, "novasenha9")

    assert usuario == bruno
    assert autenticacao.autenticar_usuario(EMAIL, "novasenha9") == bruno
    with pytest.raises(CredenciaisInvalidas):
        autenticacao.autenticar_usuario(EMAIL, SENHA)


def test_codigo_so_pode_ser_usado_uma_vez(autenticacao, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    autenticacao.redefinir_senha(EMAIL, codigo.codigo, "novasenha9")
    with pytest.raises(CodigoRecuperacaoInvalido):
        autenticacao.redefinir_senha(EMAIL, codigo.codigo, "outrasenha8")


def test_codigo_errado_nao_troca_a_senha(autenticacao, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    errado = "000000" if codigo.codigo != "000000" else "111111"
    with pytest.raises(CodigoRecuperacaoInvalido):
        autenticacao.redefinir_senha(EMAIL, errado, "novasenha9")
    assert autenticacao.autenticar_usuario(EMAIL, SENHA) == bruno


def test_codigo_vencido_e_recusado(autenticacao, agora_auth, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    agora_auth.agora += timedelta(minutes=16)
    with pytest.raises(CodigoRecuperacaoInvalido, match="venceu"):
        autenticacao.redefinir_senha(EMAIL, codigo.codigo, "novasenha9")


def test_codigo_novo_invalida_o_anterior(autenticacao, bruno):
    primeiro = autenticacao.recuperar_acesso(EMAIL)
    segundo = autenticacao.recuperar_acesso(EMAIL)
    if primeiro.codigo != segundo.codigo:  # 1 chance em 1 milhão de serem iguais
        with pytest.raises(CodigoRecuperacaoInvalido):
            autenticacao.redefinir_senha(EMAIL, primeiro.codigo, "novasenha9")
    assert autenticacao.redefinir_senha(EMAIL, segundo.codigo, "novasenha9") == bruno


def test_redefinir_sem_pedir_recuperacao_levanta_erro(autenticacao, bruno):
    with pytest.raises(CodigoRecuperacaoInvalido):
        autenticacao.redefinir_senha(EMAIL, "123456", "novasenha9")


def test_nova_senha_fraca_e_recusada_e_o_codigo_continua_valendo(autenticacao, bruno):
    codigo = autenticacao.recuperar_acesso(EMAIL)
    with pytest.raises(DadosInvalidos):
        autenticacao.redefinir_senha(EMAIL, codigo.codigo, "curta")
    assert autenticacao.redefinir_senha(EMAIL, codigo.codigo, "novasenha9") == bruno
