#!/usr/bin/env python3
"""
NovoBank Terminal — Gateway HTTP, Proxy CORS & Daemon RFID (Raspberry Pi / PC)
===============================================================================

Este script unifica a execução do frontend NovoBank (`Interface/`) com o backend
Flask real do projeto (`src/trabalho_bb/routers/bank_router.py`):

1. Serve os arquivos estáticos da pasta `Interface/` na porta 8080 (`ThreadingHTTPServer`).
2. Faz proxy reverso de `/api/*` e `/health` -> `http://127.0.0.1:5000` com cabeçalhos CORS,
   permitindo usar a interface sem alterações no backend da equipe.
3. Caso a porta 5000 ainda não esteja em execução (ex.: rodando localmente sem Docker),
   inicializa automaticamente o backend Flask `trabalho_bb` em thread em segundo plano.
4. Se `RPi.GPIO` / `SimpleMFRC522` não estiver disponível (PC Windows/Linux sem GPIO),
   injeta um leitor `tag_reader` emulado compatível com `/api/rfid` e `/api/sim-rfid`.
"""

import http.server
import json
import os
import posixpath
import queue
import socket
import sys
import threading
import time
import types
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INTERFACE_DIR = Path(__file__).resolve().parent
SRC_DIR = INTERFACE_DIR.parents[1]
PROJECT_ROOT = INTERFACE_DIR.parents[2]

HTTP_PORT = int(os.environ.get("INTERFACE_PORT", "8080"))
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "5000"))
BACKEND_URL = os.environ.get("BACKEND_URL", f"http://127.0.0.1:{BACKEND_PORT}").rstrip("/")

# Fila usada para entregar UIDs simulados ao endpoint bloqueante GET /api/rfid
SIM_RFID_QUEUE: "queue.Queue[str]" = queue.Queue()
USING_MOCK_READER = False


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def install_mock_tag_reader_if_needed() -> bool:
    """
    Importa `trabalho_bb.hardware.tag_reader` se o hardware GPIO estiver presente;
    caso contrário, registra um mock seguro em `sys.modules` compatível com `bank_router`.
    """
    global USING_MOCK_READER

    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    try:
        import trabalho_bb.hardware.tag_reader  # noqa: F401
        print("[HARDWARE] Leitor físico MFRC522 (SPI/GPIO) inicializado com sucesso.")
        USING_MOCK_READER = False
        return True
    except Exception as exc:
        print(f"[SIMULACAO] Hardware GPIO/MFRC522 indisponível ({exc}).")
        print("[SIMULACAO] Registrando driver simulado compatível com GET /api/rfid.")

        try:
            from trabalho_bb.exceptions.exceptions import RfidTimeoutError
        except Exception:
            class RfidTimeoutError(Exception):
                pass

        mock_module = types.ModuleType("trabalho_bb.hardware.tag_reader")
        mock_module.RfidTimeoutError = RfidTimeoutError

        def simulated_read_card(timeout: int = 15):
            # Esvazia leituras antigas não consumidas antes de aguardar nova aproximação
            while True:
                try:
                    SIM_RFID_QUEUE.get_nowait()
                except queue.Empty:
                    break

            try:
                uid = SIM_RFID_QUEUE.get(timeout=timeout)
                return {"rfid": str(uid)}
            except queue.Empty as empty_err:
                raise RfidTimeoutError("Timeout ao aguardar cartão RFID no simulador") from empty_err

        mock_module.read_card = simulated_read_card
        sys.modules["trabalho_bb.hardware.tag_reader"] = mock_module
        USING_MOCK_READER = True
        return False


class _NoOpRedis:
    """Cliente Redis emulado no-op quando nenhum servidor Redis está ativo localmente."""

    def get(self, *_args, **_kwargs):
        return None

    def set(self, *_args, **_kwargs):
        return True

    def delete(self, *_args, **_kwargs):
        return 0

    def close(self):
        return None


def configure_local_redis_fallback():
    """
    Evita bloqueios de DNS/TCP quando o backend Flask roda localmente fora do Docker
    sem um container `redis` ativo. Se o Redis estiver acessível, mantém-no sem alterações.
    """
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    parsed = urllib.parse.urlparse(redis_url)
    host = parsed.hostname or "redis"
    port = parsed.port or 6379
    in_docker = Path("/.dockerenv").exists()

    reachable = False
    if host == "redis" and not in_docker:
        if is_port_open("127.0.0.1", port, timeout=0.1):
            os.environ["REDIS_URL"] = f"redis://127.0.0.1:{port}/0"
            print(f"[CACHE] Redis local detectado em 127.0.0.1:{port}.")
            return
        os.environ["REDIS_URL"] = f"redis://127.0.0.1:{port}/0"
    else:
        reachable = is_port_open(host, port, timeout=0.2)
        if reachable:
            return

    try:
        import trabalho_bb.cache.redis as cache_redis

        cache_redis.redis_client = _NoOpRedis()
        print("[CACHE] Redis indisponível localmente; cache no-op ativo (<2ms, SQLite direto).")
    except ImportError:
        pass


def start_embedded_backend() -> bool:
    """Inicia o Flask `bank_router` na porta 5000 caso ainda não esteja rodando."""
    if is_port_open("127.0.0.1", BACKEND_PORT):
        print(f"[BACKEND] API Flask externa detectada em {BACKEND_URL} (modo proxy).")
        return True

    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    configure_local_redis_fallback()
    install_mock_tag_reader_if_needed()

    try:
        from trabalho_bb.repositories.bank_repository import initialize_database
        from trabalho_bb.routers.bank_router import app as flask_app
    except ImportError as exc:
        print(f"[ERRO] Dependências do backend ausentes: {exc}")
        print(
            "[DICA] Execute com: uvx --with flask --with redis --with validate-docbr "
            "python src/trabalho_bb/web/server_rfid.py"
        )
        return False

    initialize_database()
    print(f"[BACKEND] Iniciando API Flask trabalho_bb em http://127.0.0.1:{BACKEND_PORT} ...")

    def run_flask():
        flask_app.run(host="127.0.0.1", port=BACKEND_PORT, use_reloader=False, threaded=True)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    for _ in range(50):
        if is_port_open("127.0.0.1", BACKEND_PORT, timeout=0.2):
            print(f"[BACKEND] API Flask pronta em http://127.0.0.1:{BACKEND_PORT}.")
            return True
        time.sleep(0.1)

    print("[AVISO] O backend Flask demorou para abrir a porta 5000.")
    return False


class TerminalGatewayHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP que serve `Interface/` e faz proxy CORS para `/api/*` e `/health`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(INTERFACE_DIR), **kwargs)

    def log_message(self, format_str, *args):
        # Mantém log conciso para requisições de API; evita ruído excessivo de assets
        path = getattr(self, "path", "")
        if path.startswith("/api") or path == "/health":
            sys.stdout.write(f"[HTTP] {self.address_string()} - {format_str % args}\n")

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Garante recarregamento limpo durante desenvolvimento na interface
        if hasattr(self, "path") and (
            self.path == "/"
            or self.path.endswith(".html")
            or self.path.endswith(".js")
            or self.path.endswith(".css")
        ):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._proxy_request("GET", "/")
            return
        if parsed.path.startswith("/api/"):
            self._proxy_request("GET", parsed.path + (f"?{parsed.query}" if parsed.query else ""))
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/sim-rfid":
            self._handle_sim_rfid()
            return
        if parsed.path.startswith("/api/"):
            self._proxy_request("POST", parsed.path)
            return
        self.send_json(404, {"success": False, "message": "Rota não encontrada"})

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._proxy_request("PATCH", parsed.path)
            return
        self.send_json(404, {"success": False, "message": "Rota não encontrada"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._proxy_request("PUT", parsed.path)
            return
        self.send_json(404, {"success": False, "message": "Rota não encontrada"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._proxy_request("DELETE", parsed.path)
            return
        self.send_json(404, {"success": False, "message": "Rota não encontrada"})

    def _read_request_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length > 0 else b""

    def _handle_sim_rfid(self):
        if not USING_MOCK_READER:
            self.send_json(
                409,
                {
                    "success": False,
                    "message": "Leitor RFID físico ou backend externo ativo; fila emulada não vinculada.",
                },
            )
            return

        raw = self._read_request_body()
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_json(400, {"success": False, "message": "JSON inválido"})
            return

        uid = str(data.get("rfid", "")).strip()
        if not (8 <= len(uid) <= 15):
            self.send_json(
                400,
                {"success": False, "message": "RFID deve conter entre 8 e 15 caracteres"},
            )
            return

        SIM_RFID_QUEUE.put(uid)
        print(f"[SIMULACAO] Cartão injetado na fila RFID: {uid}")
        self.send_json(200, {"success": True, "rfid": uid})

    def _proxy_request(self, method: str, target_path: str):
        # Normaliza caminho para evitar redirecionamentos inesperados
        clean_path = "/" + posixpath.normpath(target_path).lstrip("/")
        if target_path == "/":
            clean_path = "/"

        target_url = f"{BACKEND_URL}{clean_path}"
        body = self._read_request_body() if method in ("POST", "PATCH", "PUT") else None
        headers = {}
        if body is not None:
            headers["Content-Type"] = self.headers.get("Content-Type", "application/json")

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        timeout_sec = 20 if clean_path.startswith("/api/rfid") else 10

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                resp_body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json; charset=utf-8")
                self._write_proxy_response(resp.status, content_type, resp_body)
        except urllib.error.HTTPError as err:
            err_body = err.read()
            content_type = err.headers.get("Content-Type", "application/json; charset=utf-8")
            self._write_proxy_response(err.code, content_type, err_body)
        except Exception as exc:
            self.send_json(
                502,
                {
                    "success": False,
                    "message": f"Backend Flask indisponível em {BACKEND_URL}: {exc}",
                },
            )

    def _write_proxy_response(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def console_rfid_input_worker():
    """Permite digitar um código RFID no console quando rodando em modo simulado."""
    if not sys.stdin or not sys.stdin.isatty():
        return

    print("[CONSOLE] Digite um RFID (8-15 chars) + Enter para simular aproximação no sensor.")
    while True:
        try:
            uid = input().strip()
            if uid:
                SIM_RFID_QUEUE.put(uid)
                print(f"[CONSOLE] Cartão enfileirado para /api/rfid: {uid}")
        except (EOFError, KeyboardInterrupt):
            break


def main():
    print("============================================================")
    print(" NovoBank Terminal — Gateway Interface + Backend trabalho_bb")
    print("============================================================")

    proxy_only = "--proxy-only" in sys.argv or os.environ.get("PROXY_ONLY") == "1"
    if proxy_only:
        print(f"[BACKEND] Modo proxy ativo (API esperada em {BACKEND_URL}).")
    else:
        start_embedded_backend()

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), TerminalGatewayHandler)

    console_thread = threading.Thread(target=console_rfid_input_worker, daemon=True)
    console_thread.start()

    print(f"[INTERFACE] Acesse no navegador: http://localhost:{HTTP_PORT}")
    print(f"[PROXY API] /api/* -> {BACKEND_URL}/api/*")
    print("============================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[ENCERRANDO] Servidor NovoBank finalizado.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
