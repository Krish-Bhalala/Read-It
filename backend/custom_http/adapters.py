import sys
import os

# Add parent directory to system path for module imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from constants import HTTPStatus, END_OF_LINE, RequestDictType


def make_cors_headers(request_headers: dict[str, str]) -> dict[str, str]:
    """
    Generates Cross-Origin Resource Sharing (CORS) headers for specific origins.

    :param request_headers: The headers from the incoming client request.
    :returns: A dictionary of CORS headers if the 'Origin' is allowed, otherwise an empty dictionary.
    """
    origin = request_headers.get("origin")
    # Check if the request origin is one of the allowed local host addresses
    if origin in ("http://localhost:8888", "http://127.0.0.1:8888"):
        return {
            "Access-Control-Allow-Origin": origin,  # Echo back the allowed origin
            "Access-Control-Allow-Methods": "GET, POST, DELETE",  # Allowed HTTP methods
            "Access-Control-Allow-Headers": "Content-Type, Authorization",  # Allowed request headers
            "Access-Control-Allow-Credentials": "true",  # Allow cookies/session info
        }
    return {}  # Return no CORS headers if origin is not allowed


def create_response(
    status: HTTPStatus,
    body_data: str | bytes = "",
    content_type: str = "text/html",
    extra_headers: dict[str, str] | None = None,
) -> bytes:
    """
    Builds the full HTTP response as bytes, combining headers and body.

    :param status: The HTTP status code (IntEnum).
    :param body_data: The content for the response body (string or bytes).
    :param content_type: The MIME type of the body content.
    :param extra_headers: Optional dictionary of additional headers to include.
    :returns: The complete HTTP response encoded as bytes.
    """
    body = b""
    try:
        # Encode the body data to bytes if it's a string
        body = (
            body_data.encode("utf-8", "ignore")
            if isinstance(body_data, str)
            else body_data
        )
    except Exception as e:
        # Print error if encoding fails
        print(f"[ADAPTERS][create_response] error in converting {body_data} {e}")

    # Start building the header lines with the status line
    lines = [f"HTTP/1.1 {status.value} {status.reason}"]
    # Add mandatory Content-Type and Content-Length headers
    lines.append(f"Content-Type: {content_type}")
    lines.append(f"Content-Length: {len(body)}")

    # Add any extra user-defined headers
    if extra_headers:
        for k, v in extra_headers.items():
            lines.append(f"{k}: {v}")

    lines.append("")  # Separator line before joining
    # Join all header lines with the standard END_OF_LINE separator
    header_part = END_OF_LINE.join(lines)
    # Combine the header (followed by an extra \r\n) and the body data
    return header_part.encode("utf-8", "ignore") + b"\r\n" + body


def parse_request(raw: str) -> RequestDictType | None:
    """
    Parses a raw HTTP request string into a structured dictionary (RequestDictType).

    :param raw: The raw HTTP request as a string.
    :returns: A RequestDictType dictionary on success, or None if the request is invalid.
    """
    lines = raw.split(END_OF_LINE)  # Split the request into individual lines
    if not lines:
        return None

    # Parse the Request Line (e.g., "GET /path?query HTTP/1.1")
    parts = lines[0].split()
    if len(parts) < 2:
        return None
    method, full_path = parts[0], parts[1]

    path = full_path
    query: dict[str, str] = {}
    # Separate path from query string if '?' exists
    if "?" in full_path:
        path, qstr = full_path.split("?", 1)
        # Parse key-value pairs in the query string
        for pair in qstr.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query[k] = v

    # Parse Headers
    headers: dict[str, str] = {}
    i = 1
    # Iterate through lines until an empty line is found (end of headers)
    while i < len(lines) and lines[i]:
        if ":" in lines[i]:
            name, value = lines[i].split(":", 1)
            # Store header names in lowercase for easier lookup
            headers[name.strip().lower()] = value.strip()
        i += 1

    # Parse Body
    body = ""
    # Check for Content-Length header to determine body size
    if "content-length" in headers:
        length = int(headers["content-length"])
        # Rejoin lines after headers to get the raw body string
        body_str = END_OF_LINE.join(lines[i + 1 :])
        # Slice the body string based on Content-Length
        body = body_str[:length].strip()

    # Return the fully parsed request dictionary
    return {
        "method": method,
        "path": path,
        "query": query,
        "headers": headers,
        "body": body,
    }
