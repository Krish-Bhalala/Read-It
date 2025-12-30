import sys
import os

# Add parent directory to system path for importing modules (e.g., constants)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from constants import (
    HTTPStatus,
    SenderFunctionType,
    RequestDictType,
    HandlerFunctionType,
    HTTPResponseType,
)

from typing import Callable, Any

# Define a type for the function returned by the 'route' decorator
DecoratorFunctionType = Callable[[HandlerFunctionType], HandlerFunctionType]

# --------------------------------------------------------------
# ROUTES: (method, path.lower()) → handler
# --------------------------------------------------------------
# Global dictionary to store registered routes. Keys are (HTTP_METHOD, PATH) tuple.
ROUTES: dict[tuple[str, str], HandlerFunctionType] = {}


def route(method: str, path: str) -> DecoratorFunctionType:
    """
    Decorator factory used to register an HTTP endpoint (method + path) to a handler function.

    :param method: The HTTP method (e.g., "GET", "POST").
    :param path: The URL path (e.g., "/api/messages").
    :returns: A decorator function that takes the handler function as an argument.
    """

    def decorator(handler: HandlerFunctionType) -> HandlerFunctionType:
        """
        The actual decorator that registers the handler.
        """
        # Create a standardized key: (UPPERCASE_METHOD, lowercase_path)
        key = (method.upper().strip(), path.lower().strip())
        if key in ROUTES:
            # Prevent registering the same route key twice
            raise ValueError(f"Route {method} {path} implementation already registered")

        # register the handler in the global list of ROUTES for dispatcher to invoke
        ROUTES[key] = handler

        # Return a function that replaces the original handler function.
        # This prevents the handler from being called directly outside of the dispatch mechanism.
        def deny_direct_call(a: Any = None, b: Any = None):
            raise Exception(
                f"Direct call to {handler.__name__} is not allowed. Use dispatch() for calling it."
            )

        return deny_direct_call

    return decorator


# Shortcuts for common HTTP methods using the route decorator factory
# get(path) is equivalent to route("GET", path)
def get(path: str) -> DecoratorFunctionType:
    return route("GET", path)


# post(path) is equivalent to route("POST", path)
def post(path: str) -> DecoratorFunctionType:
    return route("POST", path)


# delete(path) is equivalent to route("DELETE", path)
def delete(path: str) -> DecoratorFunctionType:
    return route("DELETE", path)


# --------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------
def dispatch(req: RequestDictType, send_function: SenderFunctionType) -> HTTPStatus:
    """
    Looks up the registered handler for the incoming request and executes it.

    :param req: The parsed request dictionary containing method and path.
    :param send_function: A function used by the handler to send the final HTTP response.
    :returns: An HTTPStatus code indicating the result of the dispatch (e.g., OK, NOT_FOUND).
    """
    # Create the standardized lookup key from the request
    key = (req["method"].upper().strip(), req["path"].lower().strip())
    # Retrieve the handler function from the global routes dictionary
    handler = ROUTES.get(key)
    if not handler:
        print(f"[ERROR]: dispatcher can't locate handler for {key}")
        return HTTPStatus.NOT_FOUND  # 404 if no matching route is found

    try:
        # Execute the handler function, which returns the response data
        result: HTTPResponseType = handler(req, send_function)
        # Send the final response back to the client via the provided send function
        send_function(result)
    except Exception as e:
        # Catch any exceptions that occur within the handler
        import traceback

        traceback.print_exc()  # Print full traceback for server-side debugging
        print("[ROUTER] Handler error:", e)
        return HTTPStatus.INTERNAL_ERROR  # 500 if an unhandled error occurs

    return HTTPStatus.OK  # 200 if the handler executed successfully
