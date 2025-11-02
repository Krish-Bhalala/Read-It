# main.py
import socket
import threading
import os
import time
from constants import HTTPStatus, STATIC_DIR
from http.adapters import parse_request, create_response
from socket_io.connection import send_response, handle_connection
from server.router import dispatch
from server.handlers import *

# === Shared state ===
MESSAGES: list[dict[str, str]] = []
MESSAGES_LOCK = threading.Lock()

def now_ts() -> int:
    return int(time.time() * 1000)

# === Static file serving ===
def serve_static(rel_path: str):
    path = os.path.abspath(os.path.join(STATIC_DIR, rel_path.lstrip("/")))
    if not path.startswith(os.path.abspath(STATIC_DIR)):
        # prevent accessing things outside the STATIC_DIR
        return b"Forbidden", "text/plain", HTTPStatus.FORBIDDEN
    if not os.path.isfile(path):
        return b"Not Found", "text/plain", HTTPStatus.NOT_FOUND

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
        with open(path, "rb") as f:
            return f.read(), mime, HTTPStatus.OK
    except:
        return b"Server Error", "text/plain", HTTPStatus.INTERNAL_ERROR

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
        if code == HTTPStatus.OK:
            hd["Content-Length"] = str(len(data))
        send_response(client_sock, create_response(HTTPStatus(code), data, mime, hd))
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
    def send(status: HTTPStatus, headers: dict[str, str] , body: bytes=b""):
        headers = headers or {}
        response = create_response(status, body, headers.get("Content-Type", "text/plain"), headers)
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
        print(f"Server running on {ports.backend_hostname}:{ports.backend_port}")
        while True:
            cli, _ = s.accept()
            threading.Thread(target=handle_client, args=[cli], daemon=True).start()

if __name__ == "__main__":
    main()