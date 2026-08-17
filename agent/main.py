import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv

from agent.executor import discover_commands, execute_command

load_dotenv("agent/.env")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8787"))
AGENT_TOKEN = os.environ["AGENT_TOKEN"]


class Handler(BaseHTTPRequestHandler):

    def send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {AGENT_TOKEN}"
        return secrets.compare_digest(auth, expected)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "ok": True,
                "service": "termux-agent"
            })
            return

        if self.path == "/commands":
            if not self.authorized():
                self.send_json(401, {"error": "Unauthorized"})
                return

            self.send_json(200, {
                "commands": discover_commands()
            })
            return

        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/execute":
            self.send_json(404, {"error": "Not found"})
            return

        if not self.authorized():
            self.send_json(401, {"error": "Unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw)

            command = payload.get("command")
            args = payload.get("args", [])

            if not isinstance(command, str):
                self.send_json(400, {"error": "command must be a string"})
                return

            if not isinstance(args, list) or not all(
                isinstance(x, str) for x in args
            ):
                self.send_json(400, {"error": "args must be a list of strings"})
                return

            import asyncio

            result = asyncio.run(
                execute_command(command, args)
            )

            self.send_json(200, result)

        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})

        except Exception as exc:
            self.send_json(500, {
                "error": str(exc)
            })

    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)

    print("=" * 50)
    print("Termux TeleBot Agent")
    print("=" * 50)
    print(f"Listening on: {HOST}:{PORT}")
    print("Health:   GET  /health")
    print("Commands: GET  /commands")
    print("Execute:  POST /execute")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping agent...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()