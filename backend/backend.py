import socket
from ports_config import ports
from parsers import create_response, parse_request
from constants import HTTPStatus
import threading

BUFFER_SIZE = 10240
MAX_CLIENT_WAIT_LIST = 5

def send_message(message: bytes, sock:socket.socket):
    sock.sendall(message)
    print(f"Sent To {sock.getpeername()}: {message}")

def handle_request(raw: str, client_socket:socket.socket):
    request = parse_request(raw)
    response = b""
    if not request:
        response = create_response(HTTPStatus.BAD_REQUEST)
    else:
        response = create_response(HTTPStatus.OK, b"YEAH RECEIVED UR MESSAGE")
    send_message(response, client_socket)
    print(f"Received from {client_socket.getpeername()}: {request}")


def handle_client(client_socket: socket.socket, addr: tuple[str,int]):
    while True:
        try:
            message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not message:
                break
            handle_request(message, client_socket)
        except ConnectionResetError:
            break
    client_socket.close()
    print(f"Connection with {addr} closed.")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ports.backend_hostname,ports.backend_port))
        sock.listen(MAX_CLIENT_WAIT_LIST)
        print(f"listening on port {ports.backend_port}")
        while True:
            client_socket, addr = sock.accept()
            print(f"Connected with {addr}")
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.start()

if __name__ == "__main__":  
    try:
        main()
    except:
        pass
