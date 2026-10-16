"""Demonstração do MentorHub: Agendamento e Notificações trabalhando juntos.

Roda com:  python demo.py

Esta é a "raiz de composição": o único lugar que conhece as classes concretas e
liga os componentes pelas interfaces. Os componentes em si só enxergam interfaces.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mentorhub.agendamento.componente import ComponenteAgendamento  # noqa: E402
from mentorhub.agendamento.excecoes import ErroAgendamento  # noqa: E402
from mentorhub.externos.email_simulado import EmailSimulado  # noqa: E402
from mentorhub.modelos import Papel, Usuario  # noqa: E402
from mentorhub.notificacoes.componente import ComponenteNotificacoes  # noqa: E402
from mentorhub.persistencia.memoria import PersistenciaEmMemoria  # noqa: E402

DIA = date(2030, 1, 10)
H10 = datetime(2030, 1, 10, 10, 0)
H11 = datetime(2030, 1, 10, 11, 0)


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


def mostrar_horarios(agendamento: ComponenteAgendamento) -> None:
    livres = agendamento.verificar_disponibilidade("m1", DIA)
    print("  horários livres:", [h.strftime("%H:%M") for h in livres] or "nenhum")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="  [log %(levelname)s] %(message)s")

    # --- Montagem: cria as peças e liga pelas interfaces (injeção de dependência)
    banco = PersistenciaEmMemoria()
    banco.salvar_usuario(Usuario("m1", "Ana Mentora", "ana@mentorhub.com", Papel.MENTOR))
    banco.salvar_usuario(Usuario("a1", "Bruno Mentorado", "bruno@mentorhub.com", Papel.MENTORADO))
    banco.cadastrar_horario_livre("m1", H10)
    banco.cadastrar_horario_livre("m1", H11)

    servico_email = EmailSimulado(imprimir=True)
    notificacoes = ComponenteNotificacoes(servico_email)  # exige IEmail
    agendamento = ComponenteAgendamento(banco, notificacoes)  # exige IPersistencia e INotificacao

    titulo("1. Verificar disponibilidade da mentora Ana em 10/01/2030")
    mostrar_horarios(agendamento)

    titulo("2. Agendar sessão às 10:00 (Bruno com Ana)")
    sessao = agendamento.agendar_sessao("m1", "a1", H10)
    print(f"  sessão {sessao.id} criada, status = {sessao.status.value}")
    mostrar_horarios(agendamento)

    titulo("3. Tentar agendar o mesmo horário de novo")
    try:
        agendamento.agendar_sessao("m1", "a1", H10)
    except ErroAgendamento as erro:
        print(f"  recusado: {type(erro).__name__}: {erro}")

    titulo("4. Cancelar a sessão")
    cancelada = agendamento.cancelar_sessao(sessao.id)
    print(f"  sessão {cancelada.id}, status = {cancelada.status.value}")
    mostrar_horarios(agendamento)

    titulo("5. Cancelar de novo (não pode)")
    try:
        agendamento.cancelar_sessao(sessao.id)
    except ErroAgendamento as erro:
        print(f"  recusado: {type(erro).__name__}: {erro}")

    titulo("6. Serviço de e-mail fora do ar: o agendamento continua valendo")
    servico_email.fora_do_ar = True
    sessao2 = agendamento.agendar_sessao("m1", "a1", H11)
    print(f"  sessão {sessao2.id} criada mesmo assim, status = {sessao2.status.value}")
    mostrar_horarios(agendamento)

    titulo("Resumo")
    print(f"  e-mails entregues pelo serviço simulado: {len(servico_email.enviados)}")


if __name__ == "__main__":
    main()
