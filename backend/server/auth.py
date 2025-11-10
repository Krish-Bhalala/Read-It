import threading
import time
import secrets
import re

class SessionCookie:
    def __init__(self, ttl: float, user_id: str):
        self.session_id: str = secrets.token_urlsafe(nbytes=32)
        self.expiry: float = time.time() + ttl
        self.ttl: float = ttl
        self.user_id: str = user_id
        self.cookie: str = self.create_cookie(http_only=True, max_age=int(ttl))
    
    def refresh(self):
        self.expiry = time.time() + self.ttl
        
    def create_cookie(self, path: str ="/", domain: str | None = None,
                  max_age: int = 0, secure: bool = False,
                  http_only: bool = False, same_site: str | None = None):
        parts = [f"session_id={self.session_id}", f"user={self.user_id}", f"Path={path}"]
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
        return "; ".join(parts)

ID_TO_COOKIE: dict[str, SessionCookie] = {}
cookies_lock = threading.Lock()

def start_session(user_id: str, ttl_seconds: int = 300) -> str:
    session = SessionCookie(ttl_seconds, user_id)
    with cookies_lock:
        ID_TO_COOKIE[session.session_id] = session
    return session.cookie

def _parse_session_id(cookie: str) -> str:
    match = re.search(r"session_id=([^;]+)", cookie)
    return match.group(1) if match else ""

def end_session(cookie: str) -> bool:
    session_id = _parse_session_id(cookie)
    print(f"[AUTH][end_session] {ID_TO_COOKIE}")
    if session_id != "":
        with cookies_lock:
            ID_TO_COOKIE.pop(session_id)
        return True
    else:
        print(f"[AUTH][end_session] No session id found in cookie {session_id}")
        return False

def authenticate(cookie: str) -> str | bool:
    # extract session id from cookie string using regex
    session_id = _parse_session_id(cookie)
    if session_id == "":
        return False            # Invalid cookie format, can't find the session id

    with cookies_lock:
        session = ID_TO_COOKIE.get(session_id)
        if not session:
            print(f"[AUTH] session {session_id} is no longer valid")
            return False        # session id not found
        if session.expiry > time.time():
            session.refresh()
            print("[AUTH] refreshed session")
            return session.user_id
        else:
            print(f"[AUTH] session expired {time.time() - session.ttl}")
            ID_TO_COOKIE.pop(session_id)
    return False
