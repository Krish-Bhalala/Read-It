import sys
import os
import re
import json
from typing import Any

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from constants import RequestDictType, SenderFunctionType, HTTPResponseType, HTTPStatus
from server.router import get, post, delete
from server.database_interface import query_database
from server.auth import authenticate, start_session, end_session

@get("/api/user")
def who_am_i(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    username = req.get("query", {}).get("username")
    if not username:
        print(f"[HANDLERS][who_am_i] Bad Request: Must have username field URI of request")
        return response

    if authenticate(req["headers"].get("cookie", "")) == False:
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = "Pls try logging in again to get user info as authentication failed due to invalid/expired cookies"
        return response

    request: dict[str, str] = {
        "method": "GetUser",
        "user": username,
    }
    query_result = query_database(request)
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.CREATED
        response["body"] = str(query_result["user"])
    else:
        response["status"] = HTTPStatus.NOT_FOUND
        response["body"] = f"Can't find user with username '{username}' in our system"

    return response
# curl -G -d "username=adam" -H "Cookie: session_id=<session_id>; Path=/; Max-Age=15; HttpOnly" "http://owl.cs.umanitoba.ca:8888/api/user"
"""
curl -G -d "username=adam" "http://owl.cs.umanitoba.ca:8888/api/user" -H "Cookie: session_id=<session_id>"
"""


@post("/api/register")
def register_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    username_match = re.search(r"username=([^&]+)", req.get("body", ""))
    password_match = re.search(r"password=([^&]+)", req.get("body", ""))
    username = username_match.group(1) if username_match else None
    password = password_match.group(1) if password_match else None
    if not username:
        response["body"] = f"Must have username field in the request body {req}"
        return response
    if not password:
        response["body"] = f"Must have password field in the request body {req}"
        return response

    request: dict[str, str] = {
        "method": "AddUser",
        "user": username,
        "pass": password
    }
    query_result = query_database(request)
    status = query_result.get("status", "")
    user = query_result.get("user", "")
    user_id_valid = (
        "user" in query_result and
        "id" in user and
        isinstance(user["id"], int)
    )

    if status == HTTPStatus.OK and user_id_valid:
        response["body"] = user["id"]
        response["status"] = HTTPStatus.CREATED
        response["header"]["Set-Cookie"] = start_session(username)
    elif status == HTTPStatus.RATE_LIMITED or query_result.get("error", "") == "RATE_LIMIT":
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    elif "ALREADY_EXISTS" in query_result.get("error", ""):
        response["status"] = HTTPStatus.CONFLICT
        response["body"] = f"Can't register {username} in our system, it already exists"
    else:
        print(f"[HANDLERS][register_user] Internal Error with status {status} in database query result: {query_result}")
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = f"Something wrong happened when trying to register {username} in database with status {status} and the user id validation {user_id_valid}"

    return response
# curl -X POST -d "method=AddUser&username=adam&password=yohohoho" http://owl.cs.umanitoba.ca:8888
"""
curl -X POST http://owl.cs.umanitoba.ca:8888/api/register -H "Content-Type: application/x-www-form-urlencoded" -d "username=adam&password=adam"
"""

@post("/api/login")
def login_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    username_match = re.search(r"username=([^&]+)", req.get("body", ""))
    password_match = re.search(r"password=([^&]+)", req.get("body", ""))
    username = username_match.group(1) if username_match else None
    password = password_match.group(1) if password_match else None
    if not username:
        response["body"] = f"Must have username field in the body of request {req}"
        return response
    if not password:
        response["body"] = f"Must have password field in the body of request {req}"
        return response

    request: dict[str, str] = {
        "method": "GetUser",
        "user": username,
    }
    query_result = query_database(request)
    status = query_result.get("status", "")
    user = query_result.get("user", "")
    user_id_valid = (
        "user" in query_result and
        "id" in user and
        isinstance(user["id"], int)
    )

    if status != HTTPStatus.OK or not user_id_valid:
        if status == HTTPStatus.RATE_LIMITED or query_result.get("error", "") == "RATE_LIMIT":
            response["status"] = HTTPStatus.RATE_LIMITED
            response["body"] = query_result.get("reason", "")
        elif "NO_RECORD" in query_result.get("error", ""):
            response["status"] = HTTPStatus.METHOD_NOT_ALLOWED
            response["body"] = f"username '{username}' does not exist in our system, please register first"
        else:
            print(f"[HANDLERS][login_user] Internal Error with status {status} in database query result: {query_result}")
            response["status"] = HTTPStatus.INTERNAL_ERROR
            response["body"] = (f"Something wrong happened when trying to register {username} "
                                f"in database with status {status} and the user id validation {user_id_valid}")
    else:
        response["body"] = user["id"]
        if password != user.get("pass"):
            response["status"] = HTTPStatus.METHOD_NOT_ALLOWED
            response["body"] = f"Incorrect password for user {username}"
        else:
            response["status"] = HTTPStatus.OK
            response["header"]["Set-Cookie"] = start_session(username)
            response["body"] = f"Successfully logged in user {username}"

    return response
"""
curl -X POST http://owl.cs.umanitoba.ca:8888/api/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=adam&password=yohohoho"
"""


@delete("/api/login")
def logout_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.OK,
        "header": {},
        "body": "Successfully logged out your current active session"
    }

    if end_session(req["headers"].get("cookie", "")):
        print(f"[HANDLERS][logout_user] Successfully cleared all cookies")
    else:
        print(f"[HANDLERS][logout_user] No valid session found to logout for the headers {req['headers']}")
    return response
"""
curl -X DELETE http://owl.cs.umanitoba.ca:8888/api/login -H "Cookie:<session_id>;"
"""

def _filter_messages(msgs: list[dict[str, str]], settings: dict[str, Any]) -> str:
    if settings.get("order-by") == "newest":
        msgs = list(reversed(msgs))
    if "last" in settings and isinstance(settings["last"], str) and settings["last"].isdigit():
        msgs = [msg for msg in msgs if int(msg.get("time", 0)) > int(settings["last"])]
    if "group-author" in settings:
        author = settings["group-author"]
        msgs = [msg for msg in msgs if msg.get("author", "") == author]
    return json.dumps(msgs)

@get("/api/messages")
def get_messages(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    # Authenticate the request
    if authenticate(req["headers"].get("cookie", "")) == False:
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = "Please try logging in again to get messages as authentication failed due to invalid/expired cookies"
        return response

    # Query the database for messages
    request: dict[str, str] = {
        "method": "GetMessages",
    }
    query_result = query_database(request)

    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.OK
        response["body"] = _filter_messages(query_result.get("msgs", []), req.get("query", {"order-by": "latest"}))
    elif query_result.get("status", "") == HTTPStatus.RATE_LIMITED or query_result.get("error", "") == "RATE_LIMIT":
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        print(f"[HANDLERS][get_messages] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}")
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = "Failed to retrieve messages from database"

    return response
# curl -H "Cookie: session_id=<your_session_id>; Path=/; Max-Age=15; HttpOnly" "http://owl.cs.umanitoba.ca:8888/api/messages"


@post("/api/messages")
def create_message(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    # Authenticate the request
    if authenticate(req["headers"].get("cookie", "")) == False:
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = "Please try logging in again to create a message as authentication failed due to invalid/expired cookies"
        return response

    # Parse the request body for author and message
    author_match = re.search(r"author=([^&]+)", req.get("body", ""))
    msg_match = re.search(r"msg=([^&]+)", req.get("body", ""))
    author = author_match.group(1) if author_match else None
    msg = msg_match.group(1) if msg_match else None

    if not author:
        response["body"] = f"Must have author field in the body of request"
        return response
    if not msg:
        response["body"] = f"Must have msg field in the body of request"
        return response

    # Create the new message in the database
    request: dict[str, str] = {
        "method": "NewMessage",
        "author": author,
        "msg": msg
    }
    query_result = query_database(request)
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.CREATED
        response["body"] = str(query_result.get("id", ""))
    elif query_result.get("status", "") == HTTPStatus.RATE_LIMITED or query_result.get("error", "") == "RATE_LIMIT":
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        print(f"[HANDLERS][create_message] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}")
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = "Failed to create message in database"

    return response
# curl -X POST -H "Cookie: session_id=<your_session_id>; Path=/; Max-Age=15; HttpOnly" -d "author=adam&msg=Hello%20World" "http://owl.cs.umanitoba.ca:8888/api/messages"


@delete("/api/messages")
def delete_message(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": ""
    }

    # Authenticate the request
    if authenticate(req["headers"].get("cookie", "")) == False:
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = "Please try logging in again to delete a message as authentication failed due to invalid/expired cookies"
        return response

    # Get the message ID from query parameters
    msg_id = req.get("query", {}).get("id")
    if not msg_id:
        response["body"] = f"Must have id field in the query parameters {req}"
        return response

    # Try to convert the ID to an integer
    try:
        msg_id_int = int(msg_id)
    except (ValueError, TypeError):
        response["body"] = f"Invalid message ID format: {msg_id}"
        return response

    # Delete the message from the database
    request: dict[str, str | int] = {
        "method": "DeleteMessage",
        "id": msg_id_int
    }
    query_result = query_database(request)
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.OK
        response["body"] = f"Successfully deleted message with id {msg_id_int}"
    elif query_result.get("status", "") == HTTPStatus.RATE_LIMITED or query_result.get("error", "") == "RATE_LIMIT":
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        print(f"[HANDLERS][delete_message] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}")
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = f"Failed to delete message with id {msg_id_int} from database"

    return response
# curl -X DELETE -G -d "id=9832" -H "Cookie: session_id=<your_session_id>; Path=/; Max-Age=15; HttpOnly" "http://owl.cs.umanitoba.ca:8888/api/messages"
