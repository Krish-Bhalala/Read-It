from enum import IntEnum
from typing import Callable, Any, TypedDict

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
    RATE_LIMITED = 429

    @property
    def reason(self) -> str:
        return self.name.replace("_", " ")

END_OF_LINE = "\r\n"
STATIC_DIR = "static"

# Common type hints
# FunctionType = Callable[..., Any]

class RequestDictType(TypedDict):
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: str


# handler type function will accept a dictionary of request and a function that will be used to send response
# handler will return status code, header, body for the response message
# HandlerReturnType = tuple[HTTPStatus, dict[str, Any], bytes]
class HTTPResponseType(TypedDict, total=False):
    status: HTTPStatus
    header: dict[str, Any]
    body: str

# Used by factory function in handle_client to generate sender instances for each connection
SenderFunctionType = Callable[[HTTPResponseType], None]

HandlerFunctionType = Callable[[RequestDictType, SenderFunctionType], HTTPResponseType]


DB_ADDR: tuple[str, int] = ("cormorant.cs.umanitoba.ca", 50042)