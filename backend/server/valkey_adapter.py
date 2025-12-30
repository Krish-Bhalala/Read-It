"""
Valkey Adapter Module

Translates the existing database request format to Valkey (Redis-compatible) commands.
Maintains the same request/response interface as the original database_interface.py.

Data Model:
- user:{username} → Hash: {id, user, pass}
- user:id:counter → String: auto-increment user ID
- messages → Sorted Set (score = timestamp, value = message ID)
- message:{id} → Hash: {id, author, msg, time}
- message:id:counter → String: auto-increment message ID
"""

import time
from typing import Any

import valkey

import sys
import os

# Add parent directory to system path for module imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from address_config import ValkeyConfig
from constants import HTTPStatus

# Global connection pool (created lazily)
_client: valkey.Valkey | None = None


def _get_client() -> valkey.Valkey:
    """
    Get or create a Valkey client connection using service URI.
    Uses connection pooling for efficiency.
    """
    global _client
    if _client is None:
        if not ValkeyConfig.url:
            raise ValueError("VALKEY_URL environment variable is required")

        # For SSL connections (rediss://), we need to configure SSL parameters
        connection_kwargs = {"decode_responses": True}

        # If using SSL (rediss://), add SSL certificate verification
        if ValkeyConfig.url.startswith("rediss://"):
            import ssl
            import certifi

            connection_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
            connection_kwargs["ssl_ca_certs"] = certifi.where()

        _client = valkey.from_url(ValkeyConfig.url, **connection_kwargs)
        print("[VALKEY] Connected via service URI")

    return _client


def _get_next_id(counter_key: str) -> int:
    """
    Atomically increment and return the next ID from a counter key.
    """
    client = _get_client()
    return client.incr(counter_key)


def _handle_get_user(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle GetUser request.

    Request: {"method": "GetUser", "user": "username"}
    Response: {"status": 200, "user": {"id": 1, "user": "username", "pass": "password"}}
    """
    username = request.get("user")
    if not username:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing user field"}

    client = _get_client()
    user_key = f"user:{username}"

    # Check if user exists
    if not client.exists(user_key):
        return {"status": HTTPStatus.NOT_FOUND.value, "error": "NO_RECORD"}

    # Get user data from hash
    user_data = client.hgetall(user_key)
    if not user_data:
        return {"status": HTTPStatus.NOT_FOUND.value, "error": "NO_RECORD"}

    return {
        "status": HTTPStatus.OK.value,
        "user": {
            "id": int(user_data.get("id", 0)),
            "user": user_data.get("user", username),
            "pass": user_data.get("pass", ""),
        },
    }


def _handle_add_user(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle AddUser request.

    Request: {"method": "AddUser", "user": "username", "pass": "password"}
    Response: {"status": 200, "user": {"id": 1, "user": "username", "pass": "password"}}
    """
    username = request.get("user")
    password = request.get("pass")

    if not username:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing user field"}
    if not password:
        return {
            "status": HTTPStatus.BAD_REQUEST.value,
            "error": "Missing password field",
        }

    client = _get_client()
    user_key = f"user:{username}"

    # Check if user already exists
    if client.exists(user_key):
        return {"status": HTTPStatus.CONFLICT.value, "error": "ALREADY_EXISTS"}

    # Get next user ID
    user_id = _get_next_id("user:id:counter")

    # Store user data in hash
    user_data = {"id": user_id, "user": username, "pass": password}
    client.hset(user_key, mapping=user_data)

    return {
        "status": HTTPStatus.OK.value,
        "user": {"id": user_id, "user": username, "pass": password},
    }


def _handle_get_messages(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle GetMessages request.

    Request: {"method": "GetMessages"}
    Response: {"status": 200, "msgs": [{"id": 1, "author": "user", "msg": "text", "time": 123456}]}
    """
    client = _get_client()

    # Get all message IDs from sorted set (ordered by timestamp)
    message_ids = client.zrange("messages", 0, -1)

    msgs = []
    for msg_id in message_ids:
        msg_key = f"message:{msg_id}"
        msg_data = client.hgetall(msg_key)
        if msg_data:
            msgs.append(
                {
                    "id": int(msg_data.get("id", msg_id)),
                    "author": msg_data.get("author", ""),
                    "msg": msg_data.get("msg", ""),
                    "time": int(msg_data.get("time", 0)),
                }
            )

    return {"status": HTTPStatus.OK.value, "msgs": msgs}


def _handle_new_message(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle NewMessage request.

    Request: {"method": "NewMessage", "author": "username", "msg": "message text"}
    Response: {"status": 200, "id": 12345}
    """
    author = request.get("author")
    msg = request.get("msg")

    if not author:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing author field"}
    if not msg:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing msg field"}

    client = _get_client()

    # Get next message ID
    msg_id = _get_next_id("message:id:counter")

    # Timestamp in nanoseconds (matching the original API format)
    timestamp = int(time.time() * 1_000_000_000)

    # Store message data in hash
    msg_key = f"message:{msg_id}"
    msg_data = {"id": msg_id, "author": author, "msg": msg, "time": timestamp}
    client.hset(msg_key, mapping=msg_data)

    # Add message ID to sorted set with timestamp as score
    client.zadd("messages", {str(msg_id): timestamp})

    return {"status": HTTPStatus.OK.value, "id": msg_id}


def _handle_delete_message(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle DeleteMessage request.

    Request: {"method": "DeleteMessage", "id": 12345}
    Response: {"status": 200}
    """
    msg_id = request.get("id")

    if msg_id is None:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing id field"}

    client = _get_client()
    msg_key = f"message:{msg_id}"

    # Check if message exists
    if not client.exists(msg_key):
        return {"status": HTTPStatus.NOT_FOUND.value, "error": "NO_RECORD"}

    # Delete message hash
    client.delete(msg_key)

    # Remove from sorted set
    client.zrem("messages", str(msg_id))

    return {"status": HTTPStatus.OK.value}


# Method dispatch table
_METHOD_HANDLERS = {
    "GetUser": _handle_get_user,
    "AddUser": _handle_add_user,
    "GetMessages": _handle_get_messages,
    "NewMessage": _handle_new_message,
    "DeleteMessage": _handle_delete_message,
}


def execute_query(request: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a database query by translating it to Valkey commands.

    Maintains the same request/response format as the original database interface.

    :param request: Dictionary containing the query (must have "method" key)
    :returns: Response dictionary with "status" and other relevant fields
    """
    method = request.get("method")
    print(f"[VALKEY] Executing query: {request}")
    if not method:
        return {"status": HTTPStatus.BAD_REQUEST.value, "error": "Missing method field"}

    handler = _METHOD_HANDLERS.get(method)
    if not handler:
        return {
            "status": HTTPStatus.BAD_REQUEST.value,
            "error": f"Unknown method: {method}",
        }

    try:
        return handler(request)
    except valkey.exceptions.ConnectionError as e:
        print(f"[VALKEY] Connection error: {e}")
        return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": str(e)}
    except Exception as e:
        print(f"[VALKEY] Error executing {method}: {e}")
        return {"status": HTTPStatus.INTERNAL_ERROR.value, "reason": str(e)}


if __name__ == "__main__":
    # Test the adapter
    print("Testing Valkey adapter...")

    # Test AddUser
    result = execute_query(
        {"method": "AddUser", "user": "testuser", "pass": "testpass"}
    )
    print(f"AddUser: {result}")

    # Test GetUser
    result = execute_query({"method": "GetUser", "user": "testuser"})
    print(f"GetUser: {result}")

    # Test NewMessage
    result = execute_query(
        {"method": "NewMessage", "author": "testuser", "msg": "Hello World!"}
    )
    print(f"NewMessage: {result}")

    # Test GetMessages
    result = execute_query({"method": "GetMessages"})
    print(f"GetMessages: {result}")
