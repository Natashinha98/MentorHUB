"""Sobe a API REST do Serviço de Sessões de Mentoria.

Uso:
    python servidor_api.py            # http://localhost:8000/docs (Swagger UI)
    python servidor_api.py --porta 8080
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from mentorhub.servico_sessoes.app import app  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API do Serviço de Sessões de Mentoria")
    parser.add_argument("--porta", type=int, default=8000)
    args = parser.parse_args()
    print(f"Swagger UI: http://localhost:{args.porta}/docs")
    uvicorn.run(app, host="127.0.0.1", port=args.porta)
