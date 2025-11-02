from constants import HTTPStatus, END_OF_LINE, RequestDict

def create_response(
    status: HTTPStatus,
    body: bytes = b"",
    content_type: str = "text/html",
    extra_headers: dict[str, str] | None = None
) -> bytes:

    """Build full HTTP response bytes."""
    lines = [f"HTTP/1.1 {status.value} {status.reason}"]
    lines.append(f"Content-Type: {content_type}")
    lines.append(f"Content-Length: {len(body)}")

    if extra_headers:
        for k, v in extra_headers.items():
            lines.append(f"{k}: {v}")

    lines.append("")
    header_part = END_OF_LINE.join(lines)
    return header_part.encode("utf-8") + b"\r\n" + body

def parse_request(raw: str) -> RequestDict | None:
    """Parse raw HTTP request → dict."""
    lines = raw.split(END_OF_LINE)
    if not lines:
        return None

    parts = lines[0].split()
    if len(parts) < 2:
        return None
    method, full_path = parts[0], parts[1]

    path = full_path
    query: dict[str, str] = {}
    if "?" in full_path:
        path, qstr = full_path.split("?", 1)
        for pair in qstr.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query[k] = v

    headers: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i]:
        if ":" in lines[i]:
            name, value = lines[i].split(":", 1)
            headers[name.strip().lower()] = value.strip()
        i += 1

    body = ""
    if "content-length" in headers:
        length = int(headers["content-length"])
        body_str = END_OF_LINE.join(lines[i+1:])
        body = body_str[:length].strip()

    return {
        "method": method,
        "path": path,
        "query": query,
        "headers": headers,
        "body": body
    }

if __name__ == "__main__":
    test_str = "POST /submit?course=cs&term=fall HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: test-agent\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 21\r\n\r\nname=Olivia&grade=A+\r\n"
    print(parse_request(test_str))