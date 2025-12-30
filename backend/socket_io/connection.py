import socket
import re

BUFFER_SIZE = 10240


def handle_connection(client_sock: socket.socket) -> str:
    """
    Read a full HTTP-like request from a client socket.

    This function reads chunks until the request header is complete and,
    if a Content-Length is present, until the full body is received.

    :param client_sock: The socket object for the client connection.
    :returns: The raw request data decoded as a string, or an empty string if no data received.
    """
    raw = b""  # Buffer to hold the incoming raw bytes
    while True:
        chunk = client_sock.recv(BUFFER_SIZE)  # Receive data in chunks
        if not chunk:
            break  # Connection closed or no more data to read

        raw += chunk
        header_end = raw.find(b"\r\n\r\n")  # Look for the end of the HTTP headers
        if header_end == -1:
            continue  # Headers are not yet complete, continue receiving

        # Decode header portion to search for Content-Length
        header = raw[:header_end].decode("utf-8", errors="ignore")
        # Case-insensitive regex search for Content-Length header value
        match = re.search(r"content-length:\s*(\d+)", header, re.I)
        if not match:
            break  # No Content-Length found, assume request is complete

        # If Content-Length is present, calculate the total expected length
        content_len = int(match.group(1))
        total_len = (
            header_end + 4 + content_len
        )  # Header end index + \r\n\r\n (4 bytes) + body length

        # Check if the entire request (headers + body) has been received
        if len(raw) >= total_len:
            break

    # Decode the complete raw request bytes to a string
    return raw.decode("utf-8", errors="ignore") if raw else ""


def send_response(sock: socket.socket, response_bytes: bytes):
    """
    Send full HTTP response.

    :param sock: The connected socket to send the response on.
    :param response_bytes: The complete, encoded HTTP response ready to be sent.
    """
    sock.sendall(response_bytes)  # Guarantees all bytes are sent
