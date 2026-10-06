from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)


class TransportTimeout(Exception):
    pass


class TransportFailure(Exception):
    pass


Transport = Callable[[str, str, Mapping[str, str], Optional[bytes], float], HttpResponse]
