import threading
import time
import secrets
import re


class SessionCookie:
    """
    Represents an active user session and its corresponding HTTP cookie.
    """

    def __init__(self, ttl: float, user_id: str):
        """
        Initializes a new session.

        :param ttl: Time-to-live for the session in seconds (float).
        :param user_id: Identifier for the user associated with the session.
        """
        self.session_id: str = secrets.token_urlsafe(
            nbytes=32
        )  # Generate a secure random ID
        self.expiry: float = time.time() + ttl  # Calculate initial expiration time
        self.ttl: float = ttl
        self.user_id: str = user_id
        # Create the initial Set-Cookie string with HttpOnly and Max-Age set by default
        self.cookie: str = self.create_cookie(http_only=True, max_age=int(ttl))

    def refresh(self):
        """
        Extends the session expiry time based on the original TTL.
        """
        self.expiry = time.time() + self.ttl

    def create_cookie(
        self,
        path: str = "/",
        domain: str | None = None,
        max_age: int = 0,
        secure: bool = False,
        http_only: bool = False,
        same_site: str | None = None,
    ) -> str:
        """
        Generates the 'Set-Cookie' header string for the session.

        :param path: The path the cookie applies to. Defaults to "/".
        :param domain: The domain the cookie applies to.
        :param max_age: The cookie's maximum age in seconds.
        :param secure: If True, cookie is only sent over HTTPS.
        :param http_only: If True, cookie cannot be accessed via client-side script.
        :param same_site: Controls when the cookie is sent in cross-site requests.
        :returns: The complete 'Set-Cookie' string.
        """
        # Base components of the cookie string
        parts = [
            f"session_id={self.session_id}",
            f"user={self.user_id}",
            f"Path={path}",
        ]

        # Optional attributes are appended if provided
        if domain:
            parts.append(f"Domain={domain}")
        if max_age > 0:
            parts.append(f"Max-Age={max_age}")
        if secure:
            parts.append("Secure")
        if http_only:
            parts.append("HttpOnly")
        if same_site:
            parts.append(f"SameSite={same_site}")

        # Join all parts with a semicolon and space
        return "; ".join(parts)


# Global storage for active session cookies, mapped by session ID
ID_TO_COOKIE: dict[str, SessionCookie] = {}
# Lock to ensure thread-safe access to the shared ID_TO_COOKIE dictionary
cookies_lock = threading.Lock()


def start_session(user_id: str, ttl_seconds: int = 300) -> str:
    """
    Creates a new session for a user and stores it globally.

    :param user_id: The identifier of the user logging in.
    :param ttl_seconds: The time-to-live for the session in seconds (default 5 minutes).
    :returns: The 'Set-Cookie' string to be sent back to the client.
    """
    session = SessionCookie(ttl_seconds, user_id)
    # Acquire lock before modifying shared state
    with cookies_lock:
        ID_TO_COOKIE[session.session_id] = session
    return session.cookie


def _parse_session_id(cookie: str) -> str:
    """
    Extracts the session_id value from a raw HTTP 'Cookie' header string.

    :param cookie: The raw 'Cookie' header string.
    :returns: The extracted session ID string, or an empty string if not found.
    """
    # Use regex to find the session_id key and capture its value
    match = re.search(r"session_id=([^;]+)", cookie)
    return match.group(1) if match else ""


def end_session(cookie: str) -> bool:
    """
    Deletes an active session from the global store based on the cookie string.

    :param cookie: The raw 'Cookie' header string containing the session ID.
    :returns: True if a session was found and removed, False otherwise.
    """
    session_id = _parse_session_id(cookie)
    print(f"[AUTH][end_session] {ID_TO_COOKIE}")  # Debugging: show current sessions

    if session_id != "":
        # Only attempt to pop if a session ID was parsed
        with cookies_lock:
            # Use pop to remove the session, handling KeyError if it doesn't exist
            if session_id in ID_TO_COOKIE:
                ID_TO_COOKIE.pop(session_id)
                return True
            else:
                # Session ID was parsed but not found in the dictionary (already expired/removed)
                print(
                    f"[AUTH][end_session] Session ID {session_id} not found in active list."
                )
                return False
    else:
        print(f"[AUTH][end_session] No session id found in cookie {session_id}")
        return False


def authenticate(cookie: str) -> str | bool:
    """
    Validates a session cookie: checks for existence, expiration, and refreshes if valid.

    :param cookie: The raw 'Cookie' header string from the client request.
    :returns: The authenticated user's ID (str) if valid, otherwise False.
    """
    # extract session id from cookie string using regex
    session_id = _parse_session_id(cookie)
    if session_id == "":
        return False  # Invalid cookie format, can't find the session id

    with cookies_lock:
        session = ID_TO_COOKIE.get(session_id)
        if not session:
            print(f"[AUTH] session {session_id} is no longer valid")
            return False  # session id not found in store
        # Check if the session has expired
        if session.expiry > time.time():
            session.refresh()  # Extend the session's expiration time
            print("[AUTH] refreshed session")
            return session.user_id
        else:
            # Session expired, remove it from the store
            print(f"[AUTH] session expired {time.time() - session.ttl}")
            ID_TO_COOKIE.pop(session_id)

    return False  # Authentication failed due to expiration or missing session
