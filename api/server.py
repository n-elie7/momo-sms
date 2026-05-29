import json
from http.server import BaseHTTPRequestHandler

HOST = "localhost"
PORT = 8080

class MoMoHandler(BaseHTTPRequestHandler):

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status_code, message):
        self._send_json(status_code, {"error": message, "status": status_code})

    def _require_auth(self):
        # TODO Check if authenticated first

        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"error": "Unauthorized", "status": 401}).encode()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def _read_json_body(self) -> dict | None:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            return None
        try:
            length = int(length_header)
        except ValueError:
            return None
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        
        return data if isinstance(data, dict) else None
