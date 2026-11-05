"""Testes da API REST do Serviço de Sessões de Mentoria.

Cada teste faz requisições HTTP com JSON (pelo TestClient do FastAPI) e confere o
status e o corpo da resposta definidos no contrato do serviço: as três operações
(agendarSessao, consultarSessao, cancelarSessao) e cada condição de erro prevista.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from apoio import (
    EMAIL_MENTOR,
    EMAIL_MENTORADO,
    H10,
    H11,
    HORARIO_FORA_DA_AGENDA,
    MENTOR_ID,
    MENTORADO_ID,
)
from fastapi.testclient import TestClient

from mentorhub.agendamento.componente import ComponenteAgendamento
from mentorhub.persistencia.memoria import PersistenciaEmMemoria
from mentorhub.servico_sessoes.api import criar_app
from mentorhub.servico_sessoes.excecoes import DadosInvalidos
from mentorhub.servico_sessoes.servico import ServicoSessoesMentoria

SRC = Path(__file__).resolve().parents[1] / "src"


class AgendaQueFalha(PersistenciaEmMemoria):
    """Banco em memória que pode simular a agenda fora do ar."""

    def __init__(self) -> None:
        super().__init__()
        self.agenda_fora_do_ar = False
        self.falhar_ao_salvar_sessao = False

    def salvar_sessao(self, sessao):
        if self.falhar_ao_salvar_sessao:
            raise ConnectionError("banco fora do ar")
        return super().salvar_sessao(sessao)

    def ocupar_horario(self, mentor_id, horario):
        if self.agenda_fora_do_ar:
            raise ConnectionError("agenda fora do ar")
        return super().ocupar_horario(mentor_id, horario)

    def liberar_horario(self, mentor_id, horario):
        if self.agenda_fora_do_ar:
            raise ConnectionError("agenda fora do ar")
        return super().liberar_horario(mentor_id, horario)


@pytest.fixture
def banco(persistencia) -> AgendaQueFalha:
    """Mesmos dados do fixture `persistencia`, num banco que pode falhar."""
    novo = AgendaQueFalha()
    for usuario_id in (MENTOR_ID, MENTORADO_ID):
        novo.salvar_usuario(persistencia.buscar_usuario(usuario_id))
    for horario in (H10, H11):
        novo.cadastrar_horario_livre(MENTOR_ID, horario)
    return novo


@pytest.fixture
def cliente(banco, notificacoes, relogio) -> TestClient:
    agendamento = ComponenteAgendamento(banco, notificacoes, agora=relogio)
    servico = ServicoSessoesMentoria(agendamento, banco, agora=relogio)
    return TestClient(criar_app(servico))


def agendar(cliente, mentor=MENTOR_ID, mentorado=MENTORADO_ID, horario=H10):
    return cliente.post(
        "/sessoes",
        json={"mentorId": mentor, "mentoradoId": mentorado, "horario": horario.isoformat()},
    )


def livres(cliente, data="2030-01-10"):
    return cliente.get(f"/mentores/{MENTOR_ID}/disponibilidade", params={"data": data}).json()[
        "horariosLivres"
    ]


def assert_erro(resposta, status, codigo):
    assert resposta.status_code == status, resposta.text
    corpo = resposta.json()
    assert corpo["codigo"] == codigo
    assert corpo["mensagem"]


# ------------------------------------------------------- agendarSessao: POST /sessoes


def test_agendar_responde_201_com_a_sessao_marcada(cliente):
    resposta = agendar(cliente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["sessaoId"]
    assert corpo["mentorId"] == MENTOR_ID
    assert corpo["mentoradoId"] == MENTORADO_ID
    assert corpo["horario"] == "2030-01-10T10:00:00"
    assert corpo["situacao"] == "marcada"


def test_agendar_tira_o_horario_da_agenda_do_mentor(cliente):
    assert livres(cliente) == ["2030-01-10T10:00:00", "2030-01-10T11:00:00"]
    agendar(cliente)
    assert livres(cliente) == ["2030-01-10T11:00:00"]


def test_agendar_envia_aviso_de_confirmacao_aos_dois(cliente, email):
    agendar(cliente)
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]
    assert all("confirmada" in e.assunto for e in email.enviados)


def test_mesmo_horario_duas_vezes_so_o_primeiro_e_aceito(cliente):
    assert agendar(cliente).status_code == 201
    assert_erro(agendar(cliente), 409, "HORARIO_INDISPONIVEL")


def test_horario_fora_da_agenda_do_mentor(cliente):
    assert_erro(agendar(cliente, horario=HORARIO_FORA_DA_AGENDA), 409, "HORARIO_INDISPONIVEL")


def test_mentor_inexistente(cliente):
    assert_erro(agendar(cliente, mentor="nao-existe"), 404, "MENTOR_NAO_ENCONTRADO")


def test_id_de_mentorado_nao_vale_como_mentor(cliente):
    assert_erro(agendar(cliente, mentor=MENTORADO_ID), 404, "MENTOR_NAO_ENCONTRADO")


def test_mentorado_inexistente_nao_consome_o_horario(cliente):
    assert_erro(agendar(cliente, mentorado="nao-existe"), 404, "MENTORADO_NAO_ENCONTRADO")
    assert "2030-01-10T10:00:00" in livres(cliente)


def test_horario_no_passado_e_recusado(cliente, relogio):
    relogio.agora = H10 + timedelta(minutes=1)
    resposta = agendar(cliente)
    assert_erro(resposta, 400, "DADOS_INVALIDOS")
    assert "posterior" in resposta.json()["mensagem"]


def test_campo_obrigatorio_ausente(cliente):
    resposta = cliente.post("/sessoes", json={"mentorId": MENTOR_ID, "horario": H10.isoformat()})
    assert_erro(resposta, 400, "DADOS_INVALIDOS")
    assert "mentoradoId" in resposta.json()["mensagem"]


def test_horario_em_formato_invalido(cliente):
    resposta = cliente.post(
        "/sessoes", json={"mentorId": MENTOR_ID, "mentoradoId": MENTORADO_ID, "horario": "amanhã"}
    )
    assert_erro(resposta, 400, "DADOS_INVALIDOS")
    assert "horario" in resposta.json()["mensagem"]


def test_identificador_vazio(cliente):
    assert_erro(agendar(cliente, mentor="  "), 400, "DADOS_INVALIDOS")


def test_agenda_fora_do_ar_responde_503_e_nao_cria_sessao(cliente, banco, email):
    banco.agenda_fora_do_ar = True
    assert_erro(agendar(cliente), 503, "AGENDA_INDISPONIVEL")
    banco.agenda_fora_do_ar = False
    assert "2030-01-10T10:00:00" in livres(cliente)
    assert email.enviados == []


def test_falha_no_email_nao_desfaz_o_agendamento(cliente, email):
    email.fora_do_ar = True
    resposta = agendar(cliente)
    assert resposta.status_code == 201
    sessao_id = resposta.json()["sessaoId"]
    assert cliente.get(f"/sessoes/{sessao_id}").json()["situacao"] == "marcada"


# ------------------------------------------- consultarSessao: GET /sessoes/{sessaoId}


def test_consultar_devolve_os_dados_da_sessao(cliente):
    criada = agendar(cliente).json()

    resposta = cliente.get(f"/sessoes/{criada['sessaoId']}")

    assert resposta.status_code == 200
    assert resposta.json() == criada


def test_consultar_nao_altera_nada(cliente):
    criada = agendar(cliente).json()
    antes = livres(cliente)
    cliente.get(f"/sessoes/{criada['sessaoId']}")
    assert livres(cliente) == antes
    assert cliente.get(f"/sessoes/{criada['sessaoId']}").json()["situacao"] == "marcada"


def test_consultar_sessao_inexistente(cliente):
    assert_erro(cliente.get("/sessoes/nao-existe"), 404, "SESSAO_NAO_ENCONTRADA")


# --------------------------- cancelarSessao: POST /sessoes/{sessaoId}/cancelamento


def test_cancelar_responde_200_com_a_sessao_cancelada(cliente):
    criada = agendar(cliente).json()

    resposta = cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento")

    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "cancelada"
    assert cliente.get(f"/sessoes/{criada['sessaoId']}").json()["situacao"] == "cancelada"


def test_cancelar_devolve_o_horario_a_agenda(cliente):
    criada = agendar(cliente).json()
    cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento")
    assert "2030-01-10T10:00:00" in livres(cliente)


def test_cancelar_envia_aviso_de_cancelamento(cliente, email):
    criada = agendar(cliente).json()
    email.enviados.clear()
    cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento")
    assert [e.destinatario for e in email.enviados] == [EMAIL_MENTOR, EMAIL_MENTORADO]
    assert all("cancelada" in e.assunto for e in email.enviados)


def test_cancelar_sessao_inexistente(cliente):
    assert_erro(cliente.post("/sessoes/nao-existe/cancelamento"), 404, "SESSAO_NAO_ENCONTRADA")


def test_cancelar_duas_vezes_nao_e_permitido(cliente):
    criada = agendar(cliente).json()
    cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento")
    assert_erro(
        cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento"), 409, "CANCELAMENTO_NAO_PERMITIDO"
    )


def test_nao_cancela_sessao_que_ja_aconteceu(cliente, relogio):
    criada = agendar(cliente).json()
    relogio.agora = H10 + timedelta(hours=1)
    assert_erro(
        cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento"), 409, "CANCELAMENTO_NAO_PERMITIDO"
    )


def test_agenda_fora_do_ar_no_cancelamento_mantem_a_sessao_marcada(cliente, banco):
    criada = agendar(cliente).json()
    banco.agenda_fora_do_ar = True

    assert_erro(cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento"), 503, "AGENDA_INDISPONIVEL")

    banco.agenda_fora_do_ar = False
    assert cliente.get(f"/sessoes/{criada['sessaoId']}").json()["situacao"] == "marcada"
    assert "2030-01-10T10:00:00" not in livres(cliente)


def test_falha_ao_salvar_o_cancelamento_mantem_o_horario_reservado(cliente, banco):
    criada = agendar(cliente).json()
    banco.falhar_ao_salvar_sessao = True

    assert_erro(cliente.post(f"/sessoes/{criada['sessaoId']}/cancelamento"), 503, "AGENDA_INDISPONIVEL")

    banco.falhar_ao_salvar_sessao = False
    assert cliente.get(f"/sessoes/{criada['sessaoId']}").json()["situacao"] == "marcada"
    assert "2030-01-10T10:00:00" not in livres(cliente)


def test_horario_com_fuso_e_convertido_para_o_horario_local():
    from datetime import datetime, timezone

    from mentorhub.servico_sessoes.api import _sem_fuso

    com_fuso = datetime(2030, 1, 10, 13, 0, tzinfo=timezone.utc)
    convertido = _sem_fuso(com_fuso)

    assert convertido.tzinfo is None
    assert convertido == com_fuso.astimezone().replace(tzinfo=None)
    assert _sem_fuso(H10) == H10  # sem fuso: fica como veio


def test_servico_recusa_horario_que_nao_e_data_e_hora(banco, notificacoes, relogio):
    agendamento = ComponenteAgendamento(banco, notificacoes, agora=relogio)
    servico = ServicoSessoesMentoria(agendamento, banco, agora=relogio)
    with pytest.raises(DadosInvalidos):
        servico.agendar_sessao(MENTOR_ID, MENTORADO_ID, "2030-01-10 10:00")


def test_servidor_de_demonstracao_vem_com_dados_iniciais():
    from datetime import datetime

    from mentorhub.servico_sessoes.app import montar_servico

    servico, _, email = montar_servico(imprimir_emails=False)
    cliente_demo = TestClient(criar_app(servico))
    amanha = (datetime.now() + timedelta(days=1)).date().isoformat()

    horarios = cliente_demo.get("/mentores/m1/disponibilidade", params={"data": amanha}).json()
    assert horarios["horariosLivres"] == [f"{amanha}T10:00:00", f"{amanha}T14:00:00", f"{amanha}T16:00:00"]

    resposta = cliente_demo.post(
        "/sessoes", json={"mentorId": "m1", "mentoradoId": "a1", "horario": f"{amanha}T14:00:00"}
    )
    assert resposta.status_code == 201
    assert len(email.enviados) == 2


# ------------------------------------------------------------------- documentação


def test_swagger_documenta_as_tres_operacoes(cliente):
    caminhos = cliente.get("/openapi.json").json()["paths"]
    assert "post" in caminhos["/sessoes"]
    assert "get" in caminhos["/sessoes/{sessaoId}"]
    assert "post" in caminhos["/sessoes/{sessaoId}/cancelamento"]
    assert cliente.get("/docs").status_code == 200


def test_swagger_documenta_400_e_nao_422(cliente):
    respostas = cliente.get("/openapi.json").json()["paths"]["/sessoes"]["post"]["responses"]
    assert "400" in respostas and "422" not in respostas


def test_servico_depende_so_de_interfaces():
    """Roda num Python limpo pra ver o que o serviço realmente importa."""
    proibidos = [
        "mentorhub.agendamento.componente",
        "mentorhub.persistencia.memoria",
        "mentorhub.notificacoes.componente",
        "mentorhub.externos.email_simulado",
    ]
    codigo = (
        "import sys, mentorhub.servico_sessoes.servico, mentorhub.servico_sessoes.api\n"
        f"achados = [m for m in {proibidos!r} if m in sys.modules]\n"
        "print(achados)\n"
        "sys.exit(1 if achados else 0)\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"importou implementações: {resultado.stdout}{resultado.stderr}"
