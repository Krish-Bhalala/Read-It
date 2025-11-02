from enum import IntEnum
from typing import Callable, Any

class HTTPStatus(IntEnum):
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_ERROR = 500

    @property
    def reason(self) -> str:
        return self.name.replace("_", " ")

END_OF_LINE = "\r\n"
STATIC_DIR = "static"

# Common type hints
FUNCTION_TYPE = Callable[..., Any]
from typing import TypedDict

class RequestDict(TypedDict):
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: str

# Used by factory function in handle_client to generate sender instances for each connection
SENDER_FUNCTION_TYPE = Callable[[HTTPStatus, dict[str, str], bytes], None]

# handler type function will accept a dictionary of request and a function that will be used to send response
# handler will return status code, header, body for the response message
HANDLER_RET_TYPE = tuple[HTTPStatus, dict[str, Any], bytes]
HANDLER_TYPE = Callable[[RequestDict, SENDER_FUNCTION_TYPE], HANDLER_RET_TYPE]
