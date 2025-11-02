from constants import HTTPStatus, SENDER_FUNCTION_TYPE, RequestDict, HANDLER_TYPE, HANDLER_RET_TYPE

from typing import Callable
DECORATOR_TYPE = Callable[[HANDLER_TYPE], HANDLER_TYPE]

# --------------------------------------------------------------
# ROUTES: (method, path.lower()) → handler
# --------------------------------------------------------------
ROUTES: dict[tuple[str, str], HANDLER_TYPE] = {}

def route(method: str, path: str) -> DECORATOR_TYPE:
    """
    Decorator to register an endpoint.
    Example:
        @route("GET", "/api/messages")
        def get_messages(req, send): ...
    """
    def decorator(handler: HANDLER_TYPE) -> HANDLER_TYPE:
        key = (method.upper().strip(), path.lower().strip())
        if key in ROUTES:
            raise ValueError(f"Route {method} {path} implementation already registered")

        # register the handler in the list of ROUTES for dispatcher to invoke
        ROUTES[key] = handler
        return handler
    return decorator

# Shortcuts
get: Callable[[str], DECORATOR_TYPE]     = lambda path: route("GET", path)
post: Callable[[str], DECORATOR_TYPE]    = lambda path: route("POST", path)
delete: Callable[[str], DECORATOR_TYPE]  = lambda path: route("DELETE", path)
put: Callable[[str], DECORATOR_TYPE]     = lambda path: route("PUT", path)

# --------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------
def dispatch(req: RequestDict, send_function: SENDER_FUNCTION_TYPE) -> HTTPStatus:
    """
    Call the correct handler if route exists.
    Returns True if handled.
    """
    key = (req["method"].upper().strip(), req["path"].lower().strip())
    handler = ROUTES.get(key)
    if not handler:
        print(f"[ERROR]: dispatcher can't locate handler for {key}")
        return HTTPStatus.NOT_FOUND

    try:
        result: HANDLER_RET_TYPE = handler(req, send_function)
        status, headers, body = result
        send_function(status, headers, body)
    except Exception as e:
        print("Handler error:", e)
        return HTTPStatus.INTERNAL_ERROR

    return HTTPStatus.OK