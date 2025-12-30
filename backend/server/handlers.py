import sys
import os
import re
import json
from typing import Any

# Determine the parent directory path and add it to the system path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

# Import necessary constants and utility functions
from constants import RequestDictType, SenderFunctionType, HTTPResponseType, HTTPStatus
from server.router import get, post, delete
from server.database_interface import query_database
from server.auth import authenticate, start_session, end_session


@get("/api/user")
def who_am_i(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles GET /api/user request to retrieve a user's information.

    Requires authentication and a 'username' query parameter.

    :param req: Dictionary containing request details (headers, query, body, etc.).
    :param send: Function to send the final HTTP response (unused here, used for complex streaming/async).
    :returns: Dictionary representing the HTTP response (status, header, body).
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Extract username from query parameters
    username = req.get("query", {}).get("username")
    if not username:
        print(
            "[HANDLERS][who_am_i] Bad Request: Must have username field URI of request"
        )
        response["body"] = "Username parameter is missing."
        return response

    # Check authentication via cookie
    if not authenticate(req["headers"].get("cookie", "")):
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = (
            "Pls try logging in again to get user info as authentication failed due to invalid/expired cookies"
        )
        return response

    # Prepare database query to get user details
    request: dict[str, str] = {
        "method": "GetUser",
        "user": username,
    }
    query_result = query_database(request)
    # Check if the query was successful
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = (
            HTTPStatus.CREATED
        )  # HTTP 201 is used for successful retrieval/creation
        response["body"] = str(query_result["user"])  # Return user data
    else:
        # User not found in the database
        response["status"] = HTTPStatus.NOT_FOUND
        response["body"] = f"Can't find user with username '{username}' in our system"

    return response


@post("/api/register")
def register_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles POST /api/register request to create a new user account.

    Expects 'username' and 'password' in the request body (x-www-form-urlencoded).

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Use regex to extract username and password from the request body
    username_match = re.search(r"username=([^&]+)", req.get("body", ""))
    password_match = re.search(r"password=([^&]+)", req.get("body", ""))
    username = username_match.group(1) if username_match else None
    password = password_match.group(1) if password_match else None

    # Validate required fields
    if not username:
        response["body"] = f"Must have username field in the request body {req}"
        return response
    if not password:
        response["body"] = f"Must have password field in the request body {req}"
        return response

    # Prepare database query to add the user
    request: dict[str, str] = {"method": "AddUser", "user": username, "pass": password}
    query_result = query_database(request)
    status = query_result.get("status", "")
    user = query_result.get("user", "")

    # Check if user data (including ID) was returned successfully
    user_id_valid = (
        "user" in query_result and "id" in user and isinstance(user["id"], int)
    )

    # Process database query result
    if status == HTTPStatus.OK and user_id_valid:
        response["body"] = user["id"]
        response["status"] = HTTPStatus.CREATED
        # Start a new session and set the 'Set-Cookie' header
        response["header"]["Set-Cookie"] = start_session(username)
    elif (
        status == HTTPStatus.RATE_LIMITED
        or query_result.get("error", "") == "RATE_LIMIT"
    ):
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    elif "ALREADY_EXISTS" in query_result.get("error", ""):
        # Handle conflict if the username is already taken
        response["status"] = HTTPStatus.CONFLICT
        response["body"] = f"Can't register {username} in our system, it already exists"
    else:
        # Internal server error during database operation
        print(
            f"[HANDLERS][register_user] Internal Error with status {status} in database query result: {query_result}"
        )
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = (
            f"Something wrong happened when trying to register {username} in database with status {status} and the user id validation {user_id_valid}"
        )

    return response


@post("/api/login")
def login_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles POST /api/login request to authenticate and log in a user.

    Expects 'username' and 'password' in the request body.

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Extract username and password from the request body
    username_match = re.search(r"username=([^&]+)", req.get("body", ""))
    password_match = re.search(r"password=([^&]+)", req.get("body", ""))
    username = username_match.group(1) if username_match else None
    password = password_match.group(1) if password_match else None

    # Validate required fields
    if not username:
        response["body"] = f"Must have username field in the body of request {req}"
        return response
    if not password:
        response["body"] = f"Must have password field in the body of request {req}"
        return response

    # First, query the database to retrieve the user record
    request: dict[str, str] = {
        "method": "GetUser",
        "user": username,
    }
    query_result = query_database(request)
    status = query_result.get("status", "")
    user = query_result.get("user", "")

    # Validate the existence and format of the returned user ID
    user_id_valid = (
        "user" in query_result and "id" in user and isinstance(user["id"], int)
    )

    # Check for errors or non-existence before password check
    if status != HTTPStatus.OK or not user_id_valid:
        if (
            status == HTTPStatus.RATE_LIMITED
            or query_result.get("error", "") == "RATE_LIMIT"
        ):
            response["status"] = HTTPStatus.RATE_LIMITED
            response["body"] = query_result.get("reason", "")
        elif "NO_RECORD" in query_result.get("error", ""):
            # Username not found
            response["status"] = (
                HTTPStatus.METHOD_NOT_ALLOWED
            )  # Often 401/404 are more appropriate, but 405 used here
            response["body"] = (
                f"username '{username}' does not exist in our system, please register first"
            )
        else:
            # Internal database error
            print(
                f"[HANDLERS][login_user] Internal Error with status {status} in database query result: {query_result}"
            )
            response["status"] = HTTPStatus.INTERNAL_ERROR
            response["body"] = (
                f"Something wrong happened when trying to register {username} "
                f"in database with status {status} and the user id validation {user_id_valid}"
            )
    else:
        # User record found, proceed to check password
        response["body"] = user["id"]
        if password != user.get("pass"):
            # Password mismatch
            response["status"] = (
                HTTPStatus.METHOD_NOT_ALLOWED
            )  # Again, 401 is standard, but 405 used here
            response["body"] = f"Incorrect password for user {username}"
        else:
            # Successful login
            response["status"] = HTTPStatus.OK
            response["header"]["Set-Cookie"] = start_session(
                username
            )  # Start session and set cookie
            response["body"] = f"Successfully logged in user {username}"

    return response


@delete("/api/login")
def logout_user(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles DELETE /api/login request to log out the currently active session.

    Reads the session ID from the 'Cookie' header and attempts to end the session.

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.OK,
        "header": {},
        "body": "Successfully logged out your current active session",
    }

    # Attempt to end the session using the cookie value
    if end_session(req["headers"].get("cookie", "")):
        print("[HANDLERS][logout_user] Successfully cleared all cookies")
    else:
        # Log if no valid session was found
        print(
            f"[HANDLERS][logout_user] No valid session found to logout for the headers {req['headers']}"
        )
    # Returns 200 OK regardless of whether a session was actively ended
    return response


def _filter_messages(msgs: list[dict[str, str]], settings: dict[str, Any]) -> str:
    """
    Applies filtering and sorting logic to a list of messages.

    :param msgs: The list of message dictionaries retrieved from the database.
    :param settings: A dictionary of filter settings (e.g., 'order-by', 'last', 'group-author').
    :returns: The filtered and sorted list of messages as a JSON string.
    """
    # Apply 'order-by' filter
    if settings.get("order-by") == "newest":
        msgs = list(reversed(msgs))

    # Apply 'last' (timestamp) filter to get messages newer than a specified time
    if (
        "last" in settings
        and isinstance(settings["last"], str)
        and settings["last"].isdigit()
    ):
        # Filters messages where the message time is greater than the 'last' timestamp
        msgs = [msg for msg in msgs if int(msg.get("time", 0)) > int(settings["last"])]

    # Apply 'group-author' filter
    if "group-author" in settings:
        author = settings["group-author"]
        msgs = [msg for msg in msgs if msg.get("author", "") == author]

    # Serialize the final list of messages to a JSON string
    return json.dumps(msgs)


@get("/api/messages")
def get_messages(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles GET /api/messages request to retrieve filtered and sorted messages.

    Requires authentication and supports query parameters for filtering/ordering.

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Authenticate the request using the session cookie
    if not authenticate(req["headers"].get("cookie", "")):
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = (
            "Please try logging in again to get messages as authentication failed due to invalid/expired cookies"
        )
        return response

    # Prepare database query to get all messages
    request: dict[str, str] = {
        "method": "GetMessages",
    }
    query_result = query_database(request)

    # Process database query result
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.OK
        # Filter and sort the retrieved messages before sending them in the body
        response["body"] = _filter_messages(
            query_result.get("msgs", []), req.get("query", {"order-by": "latest"})
        )
    elif (
        query_result.get("status", "") == HTTPStatus.RATE_LIMITED
        or query_result.get("error", "") == "RATE_LIMIT"
    ):
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        # Internal database error
        print(
            f"[HANDLERS][get_messages] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}"
        )
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = "Failed to retrieve messages from database"

    return response


@post("/api/messages")
def create_message(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles POST /api/messages request to submit a new message/post.

    Requires authentication and expects 'author' and 'msg' in the request body.

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Authenticate the request
    if not authenticate(req["headers"].get("cookie", "")):
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = (
            "Please try logging in again to create a message as authentication failed due to invalid/expired cookies"
        )
        return response

    # Parse the request body for author and message content
    author_match = re.search(r"author=([^&]+)", req.get("body", ""))
    msg_match = re.search(r"msg=([^&]+)", req.get("body", ""))
    author = author_match.group(1) if author_match else None
    msg = msg_match.group(1) if msg_match else None

    # Validate required fields
    if not author:
        response["body"] = "Must have author field in the body of request"
        return response
    if not msg:
        response["body"] = "Must have msg field in the body of request"
        return response

    # Prepare database query to create a new message
    request: dict[str, str] = {"method": "NewMessage", "author": author, "msg": msg}
    query_result = query_database(request)

    # Process database query result
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.CREATED  # Success
        response["body"] = str(
            query_result.get("id", "")
        )  # Return the ID of the new message
    elif (
        query_result.get("status", "") == HTTPStatus.RATE_LIMITED
        or query_result.get("error", "") == "RATE_LIMIT"
    ):
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        # Internal database error
        print(
            f"[HANDLERS][create_message] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}"
        )
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = "Failed to create message in database"

    return response


@delete("/api/messages")
def delete_message(req: RequestDictType, send: SenderFunctionType) -> HTTPResponseType:
    """
    Handles DELETE /api/messages request to delete a specific message.

    Requires authentication and expects the message 'id' in query parameters.

    :param req: Dictionary containing request details.
    :param send: Function to send the final HTTP response.
    :returns: Dictionary representing the HTTP response.
    """
    response: HTTPResponseType = {
        "status": HTTPStatus.BAD_REQUEST,
        "header": {},
        "body": "",
    }

    # Authenticate the request
    if not authenticate(req["headers"].get("cookie", "")):
        response["status"] = HTTPStatus.FORBIDDEN
        response["body"] = (
            "Please try logging in again to delete a message as authentication failed due to invalid/expired cookies"
        )
        return response

    # Get the message ID from query parameters
    msg_id = req.get("query", {}).get("id")
    if not msg_id:
        response["body"] = f"Must have id field in the query parameters {req}"
        return response

    # Try to safely convert the ID string to an integer
    try:
        msg_id_int = int(msg_id)
    except (ValueError, TypeError):
        response["body"] = f"Invalid message ID format: {msg_id}"
        return response

    # Prepare database query to delete the message by ID
    request: dict[str, str | int] = {"method": "DeleteMessage", "id": msg_id_int}
    query_result = query_database(request)

    # Process database query result
    if query_result.get("status", "") == HTTPStatus.OK:
        response["status"] = HTTPStatus.OK  # Success
        response["body"] = f"Successfully deleted message with id {msg_id_int}"
    elif (
        query_result.get("status", "") == HTTPStatus.RATE_LIMITED
        or query_result.get("error", "") == "RATE_LIMIT"
    ):
        response["status"] = HTTPStatus.RATE_LIMITED
        response["body"] = query_result.get("reason", "")
    else:
        # Internal database error or message not found/not authorized
        print(
            f"[HANDLERS][delete_message] Internal Error with status {query_result.get('status', '')} in database query result: {query_result}"
        )
        response["status"] = HTTPStatus.INTERNAL_ERROR
        response["body"] = (
            f"Failed to delete message with id {msg_id_int} from database"
        )

    return response
