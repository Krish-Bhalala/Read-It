import socket
import json
import threading
import time
from typing import Any

import sys
import os

# Add parent directory to system path for module imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from constants import HTTPStatus
from address_config import Addresses, ValkeyConfig
from server.valkey_adapter import execute_query as valkey_execute_query

# Configuration constants for rate limiting
RATE_LIMIT_COOL_DOWN = 2  # Seconds to wait after a rate limit is hit
DB_RATELIMIT_CODE = 271  # Custom status code sent by the database for rate limiting
DB_API_SUCCESS_CODE = 0  # Custom status code sent by the database for success

# Global state for rate limiting
rate_limit_lock = threading.Lock()
rate_limit_until = 0  # Timestamp (seconds) until which requests should be blocked


def send_database(sock: socket.socket, request: dict[str, Any]) -> None:
    """
    Sends a request dictionary to the database socket connection.

    The message format is: [4-byte length header] + [JSON body].

    :param sock: The connected socket to the database server.
    :param request: The dictionary containing the database query.
    """
    json_str = json.dumps(request)
    # Calculate the length of the JSON string in bytes (UTF-8 encoding)
    length = len(json_str.encode("utf-8"))
    # Convert length to a 4-byte big-endian integer
    length_bytes = length.to_bytes(4, byteorder="big", signed=False)
    # Send the length header followed by the JSON data
    sock.sendall(length_bytes + json_str.encode("utf-8"))


def receive_database(sock: socket.socket, buffer_size: int = 4096) -> dict[str, Any]:
    """
    Receives a response from the database socket connection.

    The message format is: [4-byte length header] + [JSON body].

    :param sock: The connected socket to the database server.
    :param buffer_size: The maximum number of bytes to read in one go.
    :returns: The parsed JSON response as a dictionary, or an error dictionary on failure.
    """
    RECV_SIZE = 4
    # Read the 4-byte length header first
    length_bytes = sock.recv(RECV_SIZE)
    if len(length_bytes) < RECV_SIZE:
        # Check if the header was incomplete
        return {
            "status": HTTPStatus.INTERNAL_ERROR.value,
            "reason": f"received only {len(length_bytes)} instead of {RECV_SIZE}",
        }
    # Convert the header bytes to an integer length
    length = int.from_bytes(length_bytes, byteorder="big", signed=False)

    data = b""
    # Loop to ensure all data bytes are received
    while len(data) < length:
        # Read data chunk by chunk
        more = sock.recv(min(buffer_size, length - len(data)))
        if not more:
            # Connection closed unexpectedly before all data was received
            return {
                "status": HTTPStatus.INTERNAL_ERROR.value,
                "reason": f"received only {len(data)} and still missing {length - len(data)}",
            }
        data += more

    # Decode and parse the JSON response body
    response = json.loads(data.decode("utf-8", errors="ignore"))
    status = response.get("status", HTTPStatus.INTERNAL_ERROR.value)

    # Map custom database status codes to standard HTTPStatus codes
    if status == DB_RATELIMIT_CODE:
        response["error"] = "RATE_LIMIT"
        response["status"] = HTTPStatus.RATE_LIMITED.value  # Map 271 to HTTP 429
    elif status != DB_API_SUCCESS_CODE:
        # Handle general database error codes (non-success and non-rate-limit)
        response["reason"] = "Something went wrong with db in executing query"
    else:
        # Map DB success code 0 to HTTP 200 OK
        response["status"] = HTTPStatus.OK.value

    return response


def query_database(query: dict[str, Any]) -> dict[str, Any]:
    """
    Executes a database query. Routes to Valkey adapter or legacy socket-based DB
    based on configuration.

    :param query: The dictionary containing the database query request.
    :returns: The database response dictionary, potentially modified with HTTP status codes.
    """
    global rate_limit_until

    # Use Valkey adapter if enabled
    if ValkeyConfig.use_valkey:
        return valkey_execute_query(query)

    # Legacy: Check for local rate limit before attempting connection
    with rate_limit_lock:
        if time.time() <= rate_limit_until:
            return {
                "status": HTTPStatus.RATE_LIMITED.value,
                "reason": f"Still rate limited, wait for {rate_limit_until - time.time()} sec",
            }

    try:
        # Create socket and connect to the database address
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(Addresses.database_addr)
            send_database(s, query)
            response: dict[str, Any] = receive_database(
                s
            )  # Receive and parse the response
    except Exception as e:
        # Handle connection or transmission errors
        return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": str(e)}

    # If the database responded with a rate limit, activate the local cool-down
    if response.get("status") == HTTPStatus.RATE_LIMITED.value:
        print("[DB INTERFACE] triggered rate limit from database")
        with rate_limit_lock:
            rate_limit_until = time.time() + RATE_LIMIT_COOL_DOWN  # Set the block time
            print(rate_limit_until)
        # Overwrite the db response to custom server side response
        response = {
            "status": HTTPStatus.RATE_LIMITED.value,
            "reason": f"Please retry in {RATE_LIMIT_COOL_DOWN} sec",
        }

    return response


if __name__ == "__main__":
    request: dict[str, str | int] = {"method": "DeleteMessage", "id": 498872105134}
    query_database(request)
