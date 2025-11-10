# main.py
import socket
import threading
import os
import time
from constants import HTTPStatus, STATIC_DIR
from custom_http.adapters import parse_request, create_response
from socket_io.connection import send_response, handle_connection
from server.router import dispatch
from server.handlers import *

# === Shared state ===
MESSAGES: list[dict[str, str]] = []
MESSAGES_LOCK = threading.Lock()

def now_ts() -> int:
    return int(time.time() * 1000)

# === Static file serving ===
def serve_static(rel_path: str) -> tuple[str | bytes, str, HTTPStatus]:
    path = os.path.abspath(os.path.join(STATIC_DIR, rel_path.lstrip("/")))
    if not path.startswith(os.path.abspath(STATIC_DIR)):
        # prevent accessing things outside the STATIC_DIR
        return "Forbidden", "text/plain", HTTPStatus.FORBIDDEN
    if not os.path.isfile(path):
        return f"File {path} Not Found", "text/plain", HTTPStatus.NOT_FOUND

    # get mime from static file extension
    mime = {
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg"
    }.get(os.path.splitext(path)[1].lower(), "text/plain")

    # open and send the file data
    try:
        with open(path, 'rb') as f:
            return f.read(), mime, HTTPStatus.OK
    except Exception as e:
        print(f"[serve_static] error reading file {path}: {e}")
        return f"Server Error {e}", "text/plain", HTTPStatus.INTERNAL_ERROR

# === Request handler ===
def handle_client(client_sock: socket.socket):
    raw = handle_connection(client_sock)
    if not raw:
        client_sock.close()
        return

    req = parse_request(raw)
    if not req:
        send_response(client_sock, create_response(HTTPStatus.BAD_REQUEST))
        client_sock.close()
        return

    # "/"
    if req["method"] == "GET" and req["path"] == "/":
        data, mime, code = serve_static("index.html")
        hd = {"Content-Type": mime}
        headers: dict[str, str] = {}
        if code == HTTPStatus.OK:
            headers["Content-Length"] = str(len(data))
        send_response(client_sock, create_response(HTTPStatus(code), data, mime, headers))
        client_sock.close()
        return

    # "/static_files"
    if not req["path"].startswith("/api/"):
        data, mime, code = serve_static(req["path"])
        hd = {"Content-Type": mime}
        if code == HTTPStatus.OK:
            hd["Content-Length"] = str(len(data))
        send_response(client_sock, create_response(HTTPStatus(code), data, mime, hd))
        client_sock.close()
        return

    # "/api/*"
    def send(raw_response: HTTPResponseType):
        headers = raw_response.get("header",{})
        response = create_response(
            raw_response.get("status", HTTPStatus.INTERNAL_ERROR),
            str(raw_response.get("body", "")),
            str(headers.get("Content-Type", "text/plain")),
            headers
        )
        # print(f"[MAIN][handle_client] sent response {response.decode('utf-8', 'ignore')}")
        client_sock.sendall(response)

    if dispatch(req, send):
        client_sock.close()
        return

    send_response(client_sock, create_response(HTTPStatus.NOT_FOUND))
    client_sock.close()

# === Server startup ===
def main():
    from ports_config import ports
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ports.backend_hostname, ports.backend_port))
        s.listen(5)
        print(f"Server running on {s.getsockname()[0]}:{s.getsockname()[1]}")
        while True:
            cli, _ = s.accept()
            threading.Thread(target=handle_client, args=[cli], daemon=True).start()

if __name__ == "__main__":
    main()