from __future__ import annotations

import json
from typing import Any

from agro_gps.core.transport import HttpResponse

SECRET = "agk_test_value"


def json_response(status: int, payload: Any) -> HttpResponse:
    return HttpResponse(status, json.dumps(payload).encode("utf-8"))


class FakeTransport:
    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, method, url, headers, body, timeout) -> HttpResponse:
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body, "timeout": timeout})
        if not self.responses:
            raise AssertionError(f"unexpected request {url}")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
