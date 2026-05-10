import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from db import latest_phrase, rate_latest_phrase, tag_latest_phrase

HOST = "127.0.0.1"
PORT = 5050


class FeedbackHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        if self.path == "/current":
            phrase = latest_phrase()
            if phrase is None:
                return self._send_json(404, {"error": "no phrases yet"})
            return self._send_json(200, phrase)
        return self._send_json(404, {"error": f"unknown path: {self.path}"})

    def do_POST(self) -> None:
        try:
            body = self._read_json()
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "invalid JSON"})

        if self.path == "/rate":
            try:
                rating = int(body["rating"])
            except (KeyError, ValueError, TypeError):
                return self._send_json(400, {"error": "missing or non-integer 'rating'"})
            try:
                phrase_id = rate_latest_phrase(rating)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if phrase_id is None:
                return self._send_json(404, {"error": "no phrases yet"})
            return self._send_json(200, {"phrase_id": phrase_id, "rating": rating})

        if self.path == "/tag":
            tag = body.get("tag")
            if not isinstance(tag, str) or not tag:
                return self._send_json(400, {"error": "missing or empty 'tag'"})
            remove = bool(body.get("remove", False))
            phrase_id = tag_latest_phrase(tag, remove=remove)
            if phrase_id is None:
                return self._send_json(404, {"error": "no phrases yet"})
            return self._send_json(200, {"phrase_id": phrase_id, "tag": tag, "removed": remove})

        return self._send_json(404, {"error": f"unknown path: {self.path}"})

    def log_message(self, format, *args):  # silence default access log
        pass


def main() -> None:
    server = HTTPServer((HOST, PORT), FeedbackHandler)
    print(f"feedback server on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
