from __future__ import annotations

import json

from .transport import HttpResponse

HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY = 429
HTTP_SERVER_ERROR = 500


class AgroGpsError(Exception):
    def __init__(self, message: str, code: str = "", status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class ValidationError(AgroGpsError):
    pass


class AuthError(AgroGpsError):
    pass


class ReadOnlyKeyError(AgroGpsError):
    pass


class NotFoundError(AgroGpsError):
    pass


class RateLimitError(AgroGpsError):
    pass


class ServerError(AgroGpsError):
    pass


class NetworkError(AgroGpsError):
    pass


def _envelope(response: HttpResponse) -> tuple[str, str]:
    try:
        body = json.loads(response.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return "", ""
    if not isinstance(body, dict):
        return "", ""
    return str(body.get("code") or ""), str(body.get("message") or "")


def error_from_response(response: HttpResponse) -> AgroGpsError:
    code, message = _envelope(response)
    status = response.status
    if status == HTTP_UNAUTHORIZED:
        fallback = "The key is not valid. Create one in Agro GPS > Settings > Integrations."
        return AuthError(message or fallback, code, status)
    if status == HTTP_FORBIDDEN and code == "AUT_004":
        return ReadOnlyKeyError(message or "This key is read-only; create a key with write access.", code, status)
    if status == HTTP_FORBIDDEN:
        return AuthError(message or "Not allowed with this key.", code, status)
    if status == HTTP_NOT_FOUND:
        return NotFoundError(message or "Not found.", code, status)
    if status == HTTP_TOO_MANY:
        return RateLimitError(message or "Too many requests; wait a minute.", code, status)
    if status == HTTP_BAD_REQUEST:
        return ValidationError(message or "The request was not valid.", code, status)
    if status >= HTTP_SERVER_ERROR:
        return ServerError(message or "Agro GPS is not responding; try again.", code, status)
    return AgroGpsError(message or f"Unexpected answer ({status}).", code, status)
