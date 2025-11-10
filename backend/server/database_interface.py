import socket
import json
import threading
import time
from typing import Any

import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from constants import HTTPStatus, DB_ADDR

RATE_LIMIT_COOL_DOWN = 2
DB_RATELIMIT_CODE = 271
DB_API_SUCCESS_CODE = 0

rate_limit_lock = threading.Lock()
rate_limit_until = 0

def send_database(sock: socket.socket, request: dict[str, Any]) -> None:
    json_str = json.dumps(request)
    length = len(json_str.encode('utf-8'))
    length_bytes = length.to_bytes(4, byteorder='big', signed=False)
    sock.sendall(length_bytes + json_str.encode('utf-8'))

def receive_database(sock: socket.socket, buffer_size: int = 4096) -> dict[str, Any]:
    RECV_SIZE = 4
    length_bytes = sock.recv(RECV_SIZE)
    if len(length_bytes) < RECV_SIZE:
        return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": f"received only {len(length_bytes)} instead of {RECV_SIZE}"}
    length = int.from_bytes(length_bytes, byteorder='big', signed=False)
    data = b""
    while len(data) < length:
        more = sock.recv(min(buffer_size, length - len(data)))
        if not more:
            return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": f"received only {len(data)} and still missing {length - len(data)}"}
        data += more

    response = json.loads(data.decode('utf-8', errors="ignore"))
    status = response.get("status", HTTPStatus.INTERNAL_ERROR.value)
    if status == DB_RATELIMIT_CODE:
        response["error"] = "RATE_LIMIT"
        response["status"] = HTTPStatus.RATE_LIMITED.value
    elif status != DB_API_SUCCESS_CODE:
        response["reason"] = "Something went wrong with db in executing query"
    else:
        response["status"] = HTTPStatus.OK.value

    return response

def query_database(query: dict[str, Any]) -> dict[str, Any]:
    global rate_limit_until

    with rate_limit_lock:
        if time.time() <= rate_limit_until:
            return {"status": HTTPStatus.RATE_LIMITED.value, "reason": f"Still rate limited, wait for {rate_limit_until - time.time()} sec"}

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(DB_ADDR)
            send_database(s, query)
            response: dict[str, Any] = receive_database(s)
    except Exception as e:
        return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": str(e)}

    if response.get("status") == HTTPStatus.RATE_LIMITED.value:
        print("[DB INTERFACE] triggered rate limit from database")
        with rate_limit_lock:
            rate_limit_until = time.time() + RATE_LIMIT_COOL_DOWN
        response = {"status": HTTPStatus.RATE_LIMITED.value, "reason": f"Please retry in {RATE_LIMIT_COOL_DOWN} sec"}

    return response


if __name__ == "__main__":
    test_queries: list[dict[str, Any]] = [
        {
            "query": {"method": "GetUser", "user": "adam"},
            "expected_method": "GetUser",
            "expected_keys": ["method", "status", "user"],
            "check_user": True
        },
        {
            "query": {"method": "AddUser", "user": "ZACH_HAVENS", "pass": "HAVENS_ZACH"},
            "expected_method": "AddUser",
            "expected_keys": ["method", "status", "user"],
            "check_user": True
        },
        {
            "query": {"method": "GetMessages"},
            "expected_method": "GetMessages",
            "expected_keys": ["method", "status", "msgs"],
            "check_msgs": True
        },
        {
            "query": {"method": "NewMessage", "author": "ZACH_HAVENS", "msg": "New message text."},
            "expected_method": "NewMessage",
            "expected_keys": ["method", "status", "id"]
        },
        {
            "query": {"method": "DeleteMessage", "id": 9832},
            "expected_method": "DeleteMessage",
            "expected_keys": ["method", "status"]
        }
    ]

    for test in test_queries:
        response = query_database(test["query"])
        print(f"Response for {test['query']['method']}:", response)
        assert response["method"] == test["expected_method"]
        assert all(key in response for key in test["expected_keys"])
        if test.get("check_user"):
            assert response["user"]["user"] == test["query"].get("user")
        if test.get("check_msgs"):
            assert isinstance(response["msgs"], list)


