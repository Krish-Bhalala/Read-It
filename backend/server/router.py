import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from constants import HTTPStatus, SenderFunctionType, RequestDictType, HandlerFunctionType, HTTPResponseType

from typing import Callable, Any
DecoratorFunctionType = Callable[[HandlerFunctionType], HandlerFunctionType]

# --------------------------------------------------------------
# ROUTES: (method, path.lower()) → handler
# --------------------------------------------------------------
ROUTES: dict[tuple[str, str], HandlerFunctionType] = {}

def route(method: str, path: str) -> DecoratorFunctionType:
    """
    Decorator to register an endpoint.
    Example:
        @route("GET", "/api/messages")
        def get_messages(req, send): ...
    """
    def decorator(handler: HandlerFunctionType) -> HandlerFunctionType:
        key = (method.upper().strip(), path.lower().strip())
        if key in ROUTES:
            raise ValueError(f"Route {method} {path} implementation already registered")

        # register the handler in the list of ROUTES for dispatcher to invoke
        ROUTES[key] = handler

        # Return a function that replaces the original implementation of handler function to prevent calling handlers directly without dispatch
        def deny_direct_call(a: Any = None, b: Any = None):
            raise Exception(f"Direct call to {handler.__name__} is not allowed. Use dispatch() for calling it.")
        print(f"[ROUTER] Registered route {method} {path} to handler {handler.__name__}")
        return deny_direct_call
    return decorator

# Shortcuts
get: Callable[[str], DecoratorFunctionType]     = lambda path: route("GET", path)
post: Callable[[str], DecoratorFunctionType]    = lambda path: route("POST", path)
delete: Callable[[str], DecoratorFunctionType]  = lambda path: route("DELETE", path)

# --------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------
def dispatch(req: RequestDictType, send_function: SenderFunctionType) -> HTTPStatus:
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
        result: HTTPResponseType = handler(req, send_function)
        send_function(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[ROUTER] Handler error:", e)
        return HTTPStatus.INTERNAL_ERROR

    return HTTPStatus.OK