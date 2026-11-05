"""API REST (HTTP + JSON) do Serviço de Sessões de Mentoria.

Operações do contrato:
  POST /sessoes                         -> agendarSessao()
  POST /sessoes/{sessaoId}/cancelamento -> cancelarSessao()
  GET  /sessoes/{sessaoId}              -> consultarSessao()

Apoio para testar pelo Swagger UI (Serviço de Disponibilidade, simulado):
  GET  /mentores/{mentorId}/disponibilidade?data=AAAA-MM-DD

Todo erro responde em JSON no formato {"codigo": "...", "mensagem": "..."}.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from mentorhub.modelos import Sessao
from mentorhub.servico_sessoes.excecoes import (
    AgendaIndisponivel,
    CancelamentoNaoPermitido,
    DadosInvalidos,
    ErroServicoSessoes,
    HorarioIndisponivel,
    MentoradoNaoEncontrado,
    MentorNaoEncontrado,
    SessaoNaoEncontrada,
)
from mentorhub.servico_sessoes.servico import ServicoSessoesMentoria

# Erro do contrato -> status HTTP
STATUS_HTTP = {
    DadosInvalidos: 400,
    MentorNaoEncontrado: 404,
    MentoradoNaoEncontrado: 404,
    SessaoNaoEncontrada: 404,
    HorarioIndisponivel: 409,
    CancelamentoNaoPermitido: 409,
    AgendaIndisponivel: 503,
}


# ---------------------------------------------------------------- esquemas JSON


class AgendarSessaoEntrada(BaseModel):
    """Corpo de POST /sessoes."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"mentorId": "m1", "mentoradoId": "a1", "horario": "2030-01-10T10:00:00"}
        }
    )

    mentorId: str = Field(description="Identificador do mentor escolhido.")
    mentoradoId: str = Field(description="Identificador do mentorado que solicita a sessão.")
    horario: datetime = Field(description="Data e hora da sessão (ISO 8601, horário local).")


class SessaoSaida(BaseModel):
    """Representação de uma sessão nas respostas."""

    sessaoId: str
    mentorId: str
    mentoradoId: str
    horario: datetime
    situacao: str = Field(description="marcada ou cancelada")

    @classmethod
    def de(cls, sessao: Sessao) -> "SessaoSaida":
        return cls(
            sessaoId=sessao.id,
            mentorId=sessao.mentor_id,
            mentoradoId=sessao.mentorado_id,
            horario=sessao.horario,
            situacao=sessao.status.value,
        )


class DisponibilidadeSaida(BaseModel):
    mentorId: str
    data: date
    horariosLivres: list[datetime]


class Erro(BaseModel):
    codigo: str
    mensagem: str


def _respostas(*erros: type[ErroServicoSessoes]) -> dict:
    """Documenta no Swagger os erros possíveis de cada rota."""
    respostas: dict = {}
    for erro in erros:
        status = STATUS_HTTP[erro]
        anterior = respostas.get(status, {}).get("description")
        descricao = f"{erro.codigo}: {erro.__doc__.strip()}"
        respostas[status] = {
            "model": Erro,
            "description": f"{anterior}<br>{descricao}" if anterior else descricao,
        }
    return respostas


def _sem_fuso(horario: datetime) -> datetime:
    """A agenda trabalha com horário local sem fuso; converte se vier com fuso."""
    if horario.tzinfo is not None:
        return horario.astimezone().replace(tzinfo=None)
    return horario


# ---------------------------------------------------------------- aplicação


def criar_app(servico: ServicoSessoesMentoria) -> FastAPI:
    app = FastAPI(
        title="MentorHub - Serviço de Sessões de Mentoria",
        version="1.0.0",
        description=(
            "Serviço do Bounded Context **Agendamento de Mentorias**. "
            "Permite agendar, cancelar e consultar sessões de mentoria. "
            "Erros respondem com `{\"codigo\", \"mensagem\"}`."
        ),
    )

    @app.exception_handler(ErroServicoSessoes)
    async def _erro_do_contrato(_: Request, erro: ErroServicoSessoes) -> JSONResponse:
        status = STATUS_HTTP.get(type(erro), 500)
        return JSONResponse(status_code=status, content={"codigo": erro.codigo, "mensagem": str(erro)})

    @app.exception_handler(RequestValidationError)
    async def _dados_invalidos(_: Request, erro: RequestValidationError) -> JSONResponse:
        problemas = []
        for item in erro.errors():
            campo = ".".join(str(p) for p in item.get("loc", ()) if p != "body")
            problemas.append(f"{campo or 'corpo'}: {item.get('msg')}")
        return JSONResponse(
            status_code=400,
            content={"codigo": DadosInvalidos.codigo, "mensagem": "; ".join(problemas)},
        )

    @app.post(
        "/sessoes",
        status_code=201,
        response_model=SessaoSaida,
        tags=["Sessões"],
        summary="agendarSessao(): marcar uma sessão",
        responses=_respostas(
            DadosInvalidos,
            MentorNaoEncontrado,
            MentoradoNaoEncontrado,
            HorarioIndisponivel,
            AgendaIndisponivel,
        ),
    )
    def agendar_sessao(entrada: AgendarSessaoEntrada) -> SessaoSaida:
        sessao = servico.agendar_sessao(
            entrada.mentorId, entrada.mentoradoId, _sem_fuso(entrada.horario)
        )
        return SessaoSaida.de(sessao)

    @app.get(
        "/sessoes/{sessaoId}",
        response_model=SessaoSaida,
        tags=["Sessões"],
        summary="consultarSessao(): dados e situação de uma sessão",
        responses=_respostas(SessaoNaoEncontrada),
    )
    def consultar_sessao(sessaoId: str) -> SessaoSaida:
        return SessaoSaida.de(servico.consultar_sessao(sessaoId))

    @app.post(
        "/sessoes/{sessaoId}/cancelamento",
        response_model=SessaoSaida,
        tags=["Sessões"],
        summary="cancelarSessao(): cancelar uma sessão marcada",
        responses=_respostas(SessaoNaoEncontrada, CancelamentoNaoPermitido, AgendaIndisponivel),
    )
    def cancelar_sessao(sessaoId: str) -> SessaoSaida:
        return SessaoSaida.de(servico.cancelar_sessao(sessaoId))

    @app.get(
        "/mentores/{mentorId}/disponibilidade",
        response_model=DisponibilidadeSaida,
        tags=["Apoio: disponibilidade (simulada)"],
        summary="verificarDisponibilidade(): horários livres do mentor numa data",
        responses=_respostas(MentorNaoEncontrado),
    )
    def verificar_disponibilidade(mentorId: str, data: date) -> DisponibilidadeSaida:
        livres = servico.verificar_disponibilidade(mentorId, data)
        return DisponibilidadeSaida(mentorId=mentorId, data=data, horariosLivres=livres)

    def _openapi_sem_422() -> dict:
        """O FastAPI documenta 422 por padrão; esta API responde 400 (DADOS_INVALIDOS)."""
        if app.openapi_schema is None:
            from fastapi.openapi.utils import get_openapi

            esquema = get_openapi(
                title=app.title, version=app.version, description=app.description, routes=app.routes
            )
            for caminho in esquema["paths"].values():
                for operacao in caminho.values():
                    operacao.get("responses", {}).pop("422", None)
            for nome in ("HTTPValidationError", "ValidationError"):
                esquema.get("components", {}).get("schemas", {}).pop(nome, None)
            app.openapi_schema = esquema
        return app.openapi_schema

    app.openapi = _openapi_sem_422
    return app
