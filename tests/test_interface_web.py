"""Testes da camada de aplicação e do servidor da interface web (Autenticação e Busca)."""

from __future__ import annotations

import json
import threading
import urllib.request

import pytest

from interface_web.aplicacao import Demo
from interface_web.servidor import criar_servidor

SENHA = "senha1234"


@pytest.fixture
def demo():
    return Demo(iteracoes_hash=1_000)


def entrar_como(demo, email):
    resposta = demo.entrar(email, SENHA)
    assert resposta["ok"], resposta["erro"]
    return resposta


def test_estado_inicial_sem_ninguem_logado_e_com_contas_de_teste(demo):
    estado = demo.estado()
    assert estado["usuario"] is None
    assert [c["email"] for c in estado["contas_teste"]][0] == "ana@mentorhub.com"
    assert all(c["senha"] == SENHA for c in estado["contas_teste"])


def test_servidor_http_responde_pagina_e_api():
    servidor = criar_servidor(0, Demo(iteracoes_hash=1_000))
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{porta}"
        assert "MentorHub" in urllib.request.urlopen(base + "/").read().decode()

        def post(rota, corpo):
            pedido = urllib.request.Request(
                base + rota, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}
            )
            return json.load(urllib.request.urlopen(pedido))

        assert json.load(urllib.request.urlopen(base + "/api/estado"))["estado"]["usuario"] is None
        assert post("/api/pesquisar", {"area": "python"})["erro"]["tipo"] == "NaoAutenticado"
        assert post("/api/entrar", {"email": "bruno@mentorhub.com", "senha": SENHA})["ok"]
        busca = post("/api/pesquisar", {"area": "python"})
        assert [r["nome"] for r in busca["dados"]["resultados"]][0] == "Ana Mentora"
        assert post("/api/perfil", {"perfil_id": "m1"})["dados"]["perfil"]["nome"] == "Ana Mentora"
        assert post("/api/sair", {})["estado"]["usuario"] is None
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/api/inexistente")
    finally:
        servidor.shutdown()
        servidor.server_close()


def test_login_correto_mostra_o_usuario(demo):
    resp = entrar_como(demo, "bruno@mentorhub.com")
    assert resp["estado"]["usuario"]["nome"] == "Bruno Mentorado"


def test_login_com_senha_errada_nao_loga(demo):
    resp = demo.entrar("bruno@mentorhub.com", "errada123")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "CredenciaisInvalidas"
    assert resp["estado"]["usuario"] is None


def test_cadastro_com_dados_ruins_devolve_a_lista_de_erros(demo):
    resp = demo.cadastrar("B", "sem-arroba", "curta", "mentorado")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "DadosInvalidos"
    assert len(resp["erro"]["detalhes"]) >= 3


def test_cadastro_com_papel_invalido_e_recusado(demo):
    resp = demo.cadastrar("Nova Pessoa", "nova@mentorhub.com", "outrasenha77", "chefe")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "DadosInvalidos"


def test_cadastro_valido_cria_conta_e_permite_entrar(demo):
    resp = demo.cadastrar("Nova Pessoa", "nova@mentorhub.com", "outrasenha77", "mentorado")
    assert resp["ok"] and resp["estado"]["usuario"] is None  # cadastrar não loga sozinho
    assert demo.entrar("nova@mentorhub.com", "outrasenha77")["ok"]


def test_mentor_novo_aparece_na_busca(demo):
    demo.cadastrar("Fábio Novo", "fabio@mentorhub.com", "outrasenha77", "mentor", "Design, Carreira", "Designer.")
    entrar_como(demo, "bruno@mentorhub.com")
    nomes = [r["nome"] for r in demo.pesquisar("design")["dados"]["resultados"]]
    assert nomes == ["Fábio Novo"]


def test_mentor_novo_sem_areas_cai_em_geral(demo):
    demo.cadastrar("Fábio Novo", "fabio@mentorhub.com", "outrasenha77", "mentor")
    entrar_como(demo, "bruno@mentorhub.com")
    assert [r["nome"] for r in demo.pesquisar("geral")["dados"]["resultados"]] == ["Fábio Novo"]


def test_recuperacao_de_senha_completa(demo):
    codigo = demo.recuperar_acesso("bruno@mentorhub.com")["dados"]["codigo"]
    assert demo.redefinir_senha("bruno@mentorhub.com", codigo, "senhanova55")["ok"]
    assert demo.entrar("bruno@mentorhub.com", "senhanova55")["ok"]


def test_redefinir_com_codigo_errado_falha(demo):
    demo.recuperar_acesso("bruno@mentorhub.com")
    resp = demo.redefinir_senha("bruno@mentorhub.com", "000000", "senhanova55")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "CodigoRecuperacaoInvalido"


def test_recuperar_acesso_de_email_desconhecido(demo):
    resp = demo.recuperar_acesso("ninguem@mentorhub.com")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "ContaNaoEncontrada"


def test_busca_e_perfil_exigem_login(demo):
    assert demo.pesquisar("python")["erro"]["tipo"] == "NaoAutenticado"
    assert demo.perfil("m1")["erro"]["tipo"] == "NaoAutenticado"


def test_busca_devolve_resultados_ordenados_com_foto(demo):
    entrar_como(demo, "bruno@mentorhub.com")
    resultados = demo.pesquisar("python")["dados"]["resultados"]
    assert [r["nome"] for r in resultados][:2] == ["Ana Mentora", "Carlos Mentor"]
    assert resultados[0]["foto"].startswith("data:image/svg+xml;base64,")


def test_busca_com_area_vazia_devolve_erro_de_dominio(demo):
    entrar_como(demo, "bruno@mentorhub.com")
    resp = demo.pesquisar("   ")
    assert resp["ok"] is False and resp["erro"]["tipo"] == "AreaInvalida"


def test_perfil_traz_bio_e_avaliacoes(demo):
    entrar_como(demo, "bruno@mentorhub.com")
    perfil = demo.perfil("m1")["dados"]["perfil"]
    assert perfil["nome"] == "Ana Mentora" and perfil["bio"]
    assert len(perfil["avaliacoes"]) == 3
    assert demo.perfil("a1")["erro"]["tipo"] == "PerfilNaoEncontrado"


def test_sair_e_reiniciar_deslogam(demo):
    entrar_como(demo, "bruno@mentorhub.com")
    assert demo.sair()["estado"]["usuario"] is None
    entrar_como(demo, "bruno@mentorhub.com")
    demo.reiniciar()
    assert demo.estado()["usuario"] is None
