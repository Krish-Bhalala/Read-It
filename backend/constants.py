from enum import IntEnum

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