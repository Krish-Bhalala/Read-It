import socket
import re

BUFFER_SIZE = 10240

def handle_connection(client_sock: socket.socket) -> str:
    """Read a full HTTP-like request from a client socket."""
    raw = b""
    while True:
        chunk = client_sock.recv(BUFFER_SIZE)
        if not chunk:
            break

        raw += chunk
        header_end = raw.find(b"\r\n\r\n")
        if header_end == -1:
            continue

        header = raw[:header_end].decode('utf-8', errors='ignore')
        match = re.search(r"content-length:\s*(\d+)", header, re.I)
        if not match:
            break

        content_len = int(match.group(1))
        total_len = header_end + 4 + content_len
        if len(raw) >= total_len:
            break

    return raw.decode('utf-8', errors='ignore') if raw else ""


def send_response(sock: socket.socket, response_bytes: bytes):
    """Send full HTTP response."""
    sock.sendall(response_bytes)