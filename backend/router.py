from constants import HTTPStatus

from typing import Callable, Any

FUNCTION = Callable[..., Any]
# handler type function will accept a dictionary of request and a function that will be used to send response
# handler will return status code, header, body for the response message
HANDLER_RET_TYPE = tuple[HTTPStatus, dict[str, Any], bytes]
HANDLER_TYPE = Callable[[dict[str, Any], FUNCTION], HANDLER_RET_TYPE]

# --------------------------------------------------------------
# ROUTES: (method, path.lower()) → handler
# --------------------------------------------------------------
ROUTES: dict[tuple[str, str], HANDLER_TYPE] = {}

def route(method: str, path: str) -> FUNCTION:
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
get: Callable[[str], FUNCTION]     = lambda path: route("GET", path)
post: Callable[[str], FUNCTION]    = lambda path: route("POST", path)
delete: Callable[[str], FUNCTION]  = lambda path: route("DELETE", path)
put: Callable[[str], FUNCTION]     = lambda path: route("PUT", path)

# --------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------
def dispatch(req: dict[str, Any], send_function: FUNCTION) -> HTTPStatus:
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
        return HTTPStatus.INTERNAL_SERVER_ERROR

    return HTTPStatus.OK