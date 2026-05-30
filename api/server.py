import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from auth import is_authenticated
from store import TransactionStore
import re

# allowing `python api/server.py` from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HOST = "localhost"
PORT = 8080
ROUTE_COLLECTION = re.compile(r"^/transactions/?$")
ROUTE_ITEM = re.compile(r"^/transactions/(\d+)/?$")

DEFAULT_XML_PATH = Path(__file__).resolve().parent.parent / "data" / "modified_sms_v2.xml"
STORE = TransactionStore()


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
        auth_header = self.headers.get("Authorization")
        if is_authenticated(auth_header):
            return True

        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")

        body = json.dumps({
                "error": "Unauthorized", 
                "status": 401
            }).encode()

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

    # overwrote default access log; replace with cleaner formatting
    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self) -> None:
        if not self._require_auth():
            return
 
        # GET /transactions list everything
        if ROUTE_COLLECTION.match(self.path):
            self._send_json(200, {
                "count": STORE.count(),
                "transactions": STORE.list_all(),
            })
            return
 
        # GET /transactions/{id} one record
        match = ROUTE_ITEM.match(self.path)
        if match:
            transaction_id = int(match.group(1))
            record = STORE.get(transaction_id)
            if record is None:
                self._send_error(404, f"Transaction {transaction_id} not found")
                return
            self._send_json(200, record)
            return
 
        self._send_error(404, f"No such endpoint: {self.path}")
 
    def do_POST(self) -> None:
        if not self._require_auth():
            return
 
        if not ROUTE_COLLECTION.match(self.path):
            self._send_error(404, f"POST not allowed on {self.path}")
            return
 
        payload = self._read_json_body()
        if payload is None:
            self._send_error(400, "Request body must be a JSON object")
            return
 
        # body is essential
        if "body" not in payload or not isinstance(payload["body"], str):
            self._send_error(400, "Field 'body' (string) is required")
            return
 
        record = STORE.create(payload)
        
        body = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Location", f"/transactions/{record['id']}")
        self.end_headers()
        self.wfile.write(body)
 
    def do_PUT(self) -> None:
        if not self._require_auth():
            return
 
        match = ROUTE_ITEM.match(self.path)
        if not match:
            self._send_error(404, f"PUT requires /transactions/{id}")
            return
 
        transaction_id = int(match.group(1))
        payload = self._read_json_body()
        if payload is None:
            self._send_error(400, "Request body must be a JSON object")
            return
 
        updated = STORE.update(transaction_id, payload)
        if updated is None:
            self._send_error(404, f"Transaction {transaction_id} not found")
            return
 
        self._send_json(200, updated)
 
    def do_DELETE(self) -> None:
        if not self._require_auth():
            return
 
        match = ROUTE_ITEM.match(self.path)
        if not match:
            self._send_error(404, f"DELETE requires /transactions/{id}")
            return
 
        transaction_id = int(match.group(1))
        if not STORE.delete(transaction_id):
            self._send_error(404, f"Transaction {transaction_id} not found")
            return
 
        # 204 No Content is the standard "success, nothing to return" code
        self.send_response(204)
        self.end_headers()
 

def main() -> None:
    # allow overriding the XML path on the command line
    xml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XML_PATH
    if not xml_path.exists():
        # Fall back to the dev path
        xml_path = Path("/mnt/user-data/uploads/modified_sms_v2.xml")
 
    print(f"Loading transactions from {xml_path}...")
    count = STORE.load_from_xml(xml_path)
    print(f"Loaded {count} transactions into memory\n")
 
    server = HTTPServer((HOST, PORT), MoMoHandler)
    print(f"MoMo API running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()
 
 
if __name__ == "__main__":
    main()
