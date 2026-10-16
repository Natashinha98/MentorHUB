"""Servidor local da interface (Autenticação e Busca de Mentores; só biblioteca padrão).

Rode com:  python interface_web/servidor.py
Depois abra http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))

from interface_web.aplicacao import Demo  # noqa: E402

PAGINA = Path(__file__).resolve().parent / "index.html"


def criar_servidor(porta: int, demo: Demo | None = None) -> ThreadingHTTPServer:
    demo = demo or Demo()

    class Manipulador(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):  # silencia o log de cada requisição
            pass

        def _enviar(self, codigo: int, tipo: str, corpo: bytes) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, dados: dict, codigo: int = 200) -> None:
            self._enviar(codigo, "application/json; charset=utf-8", json.dumps(dados, ensure_ascii=False).encode())

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                self._enviar(200, "text/html; charset=utf-8", PAGINA.read_bytes())
            elif url.path == "/api/estado":
                self._json({"ok": True, "estado": demo.estado()})
            else:
                self._enviar(404, "text/plain; charset=utf-8", b"nao encontrado")

        def do_POST(self):
            tamanho = int(self.headers.get("Content-Length") or 0)
            c = json.loads(self.rfile.read(tamanho) or b"{}")
            rotas = {
                "/api/entrar": lambda: demo.entrar(c.get("email"), c.get("senha")),
                "/api/sair": demo.sair,
                "/api/cadastrar": lambda: demo.cadastrar(
                    c.get("nome"), c.get("email"), c.get("senha"), c.get("papel"), c.get("area"), c.get("bio")
                ),
                "/api/recuperar": lambda: demo.recuperar_acesso(c.get("email")),
                "/api/redefinir": lambda: demo.redefinir_senha(c.get("email"), c.get("codigo"), c.get("nova_senha")),
                "/api/pesquisar": lambda: demo.pesquisar(c.get("area")),
                "/api/perfil": lambda: demo.perfil(c.get("perfil_id")),
            }
            rota = urlparse(self.path).path
            if rota in rotas:
                self._json(rotas[rota]())
            else:
                self._enviar(404, "text/plain; charset=utf-8", b"nao encontrado")

    return ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interface de demonstração do MentorHub")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador sozinho")
    args = parser.parse_args()

    servidor = criar_servidor(args.porta)
    endereco = f"http://localhost:{args.porta}"
    print(f"MentorHub rodando em {endereco}  (Ctrl+C para parar)")
    if not args.sem_navegador:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
