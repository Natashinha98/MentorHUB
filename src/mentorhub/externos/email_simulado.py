"""Serviço de e-mail simulado: implementa IEmail sem mandar e-mail de verdade.

No projeto real, uma classe parecida falaria com a API de e-mail reutilizada.
Aqui as mensagens ficam numa lista (`enviados`), o que deixa os testes e a demo
conferirem exatamente o que seria enviado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from mentorhub.notificacoes.excecoes import FalhaEnvioEmail
from mentorhub.notificacoes.interfaces import IEmail


@dataclass(frozen=True)
class EmailEnviado:
    destinatario: str
    assunto: str
    corpo: str


class EmailSimulado(IEmail):
    def __init__(
        self,
        imprimir: bool = False,
        destinatarios_com_falha: Iterable[str] = (),
    ) -> None:
        self.enviados: list[EmailEnviado] = []
        self.imprimir = imprimir
        # Pra simular o serviço fora do ar (todos) ou um endereço específico com problema.
        self.fora_do_ar = False
        self.destinatarios_com_falha = set(destinatarios_com_falha)

    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        if self.fora_do_ar or destinatario in self.destinatarios_com_falha:
            raise FalhaEnvioEmail("serviço de e-mail indisponível")
        self.enviados.append(EmailEnviado(destinatario, assunto, corpo))
        if self.imprimir:
            print(f"    [e-mail simulado] para={destinatario} | {assunto} | {corpo}")
