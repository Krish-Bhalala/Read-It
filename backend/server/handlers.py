from constants import RequestDict, SENDER_FUNCTION_TYPE, HANDLER_RET_TYPE
from server.router import get, post, delete

@get("/api/user")
def register_user(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@post("/api/login")
def login_user(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@delete("/api/login")
def logout_user(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@get("/api/login")
def whoami(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@get("/api/messages")
def get_messages(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@post("/api/messages")
def create_message(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass

@delete("/api/messages")
def delete_message(req: RequestDict, send: SENDER_FUNCTION_TYPE) -> HANDLER_RET_TYPE:
    pass