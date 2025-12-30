# main.py
import socket
import threading
import os
import time

# my custom modules
from constants import HTTPStatus, STATIC_DIR
from address_config import Addresses
from custom_http.adapters import parse_request, create_response
from socket_io.connection import send_response, handle_connection
from server.router import dispatch
from server.handlers import *


def now_ts() -> int:
    """
    Generates a current timestamp in milliseconds (integer).

    :returns: The current time as an integer in milliseconds.
    """
    # time.time() returns seconds since epoch as float. Multiply by 1000 for ms.
    return int(time.time() * 1000)


# === Static file serving ===
def serve_static(rel_path: str) -> tuple[str | bytes, str, HTTPStatus]:
    """
    Serves static files from the STATIC_DIR.

    :param rel_path: The relative path to the file requested (e.g., "/index.html").
    :returns: A tuple containing (file_data, MIME_type, HTTPStatus_code).
    """
    # Construct absolute path, ensuring it stays within the STATIC_DIR.
    path = os.path.abspath(os.path.join(STATIC_DIR, rel_path.lstrip("/")))
    if not path.startswith(os.path.abspath(STATIC_DIR)):
        # Security check: prevent accessing files outside the STATIC_DIR (Directory Traversal).
        return "Forbidden", "text/plain", HTTPStatus.FORBIDDEN
    if not os.path.isfile(path):
        # Check if the requested path actually points to a file.
        return f"File {path} Not Found", "text/plain", HTTPStatus.NOT_FOUND

    # Define common MIME types based on file extension.
    mime = {
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }.get(os.path.splitext(path)[1].lower(), "text/plain")

    # Attempt to open and read the file data in binary mode.
    try:
        with open(path, "rb") as f:
            data = f.read()

        # Inject backend config into app.js
        if rel_path.lstrip("/") == "app.js":
            host, port = Addresses.backend_addr
            api_base = f"http://{host}:{port}/api"
            data = data.replace(b"{{API_BASE}}", api_base.encode("utf-8"))

        return data, mime, HTTPStatus.OK
    except Exception as e:
        # Catch any file reading errors (e.g., permissions).
        print(f"[serve_static] error reading file {path}: {e}")
        return f"Server Error {e}", "text/plain", HTTPStatus.INTERNAL_ERROR


# === Request handler ===
def handle_client(client_sock: socket.socket):
    """
    Handles a single client connection: reads request, dispatches, and sends response.

    :param client_sock: The socket object for the client connection.
    """
    # Read raw data from the client connection.
    raw = handle_connection(client_sock)
    if not raw:
        client_sock.close()
        return

    # Parse the raw HTTP request data into a dictionary structure.
    req = parse_request(raw)
    if not req:
        # Handle cases where the request is malformed.
        send_response(client_sock, create_response(HTTPStatus.BAD_REQUEST))
        client_sock.close()
        return

    # Special handling for the root path "/" (serves index.html).
    if req["method"] == "GET" and req["path"] == "/":
        data, mime, code = serve_static("index.html")
        hd = {"Content-Type": mime}
        headers: dict[str, str] = {}
        if code == HTTPStatus.OK:
            # Set Content-Length header for successful responses.
            headers["Content-Length"] = str(len(data))
        # Create and send the complete HTTP response.
        send_response(
            client_sock, create_response(HTTPStatus(code), data, mime, headers)
        )
        client_sock.close()
        return

    # Handling for all other static files (paths not starting with /api/).
    if not req["path"].startswith("/api/"):
        data, mime, code = serve_static(req["path"])
        hd = {"Content-Type": mime}
        if code == HTTPStatus.OK:
            hd["Content-Length"] = str(len(data))
        # Send the static file response.
        send_response(client_sock, create_response(HTTPStatus(code), data, mime, hd))
        client_sock.close()
        return

    # Handling for API requests (paths starting with /api/*).
    def send(raw_response: HTTPResponseType):
        """
        Helper function to format and send the response for API calls.

        :param raw_response: Dictionary containing status, body, and header from the handler.
        """
        headers = raw_response.get("header", {})
        response = create_response(
            raw_response.get("status", HTTPStatus.INTERNAL_ERROR),
            str(raw_response.get("body", "")),
            str(headers.get("Content-Type", "text/plain")),
            headers,
        )
        # Send the final encoded response back to the client.
        client_sock.sendall(response)

    # Dispatch the request to the API router.
    if dispatch(req, send):
        # Dispatch returns True if a handler was found and responded, close connection.
        client_sock.close()
        return

    # If dispatch returns False (no route found in the API).
    send_response(client_sock, create_response(HTTPStatus.NOT_FOUND))
    client_sock.close()


# === Server startup ===
def main():
    """Initializes and runs the main socket server loop."""
    from address_config import Addresses

    # Create an IPv4 TCP socket (AF_INET, SOCK_STREAM).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Allow reuse of the address/port immediately after the server stops.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to the configured hostname and port.
        s.bind(Addresses.backend_addr)
        # Start listening for incoming connections (queue size 5).
        s.listen(5)
        print(f"Server running on {s.getsockname()[0]}:{s.getsockname()[1]}")
        while True:
            # Accept a new client connection.
            cli, _ = s.accept()
            # Start a new thread to handle the client request concurrently.
            threading.Thread(target=handle_client, args=[cli], daemon=True).start()


if __name__ == "__main__":
    main()
