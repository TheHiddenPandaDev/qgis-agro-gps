from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Any

from .errors import ValidationError

DRAWN_PREFIX = "DRAWN-"
QGIS_ID_PREFIX = "DRAWN-qgis-"
MAX_NAME_LENGTH = 120
MIN_POINTS = 3
MAX_POINTS = 5000
COORDINATE_DECIMALS = 7
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


def field_payload(name: str, country: str, outer_ring_lon_lat: Sequence[Sequence[float]], crop_code: str = "",
                  field_id: str | None = None) -> dict[str, Any]:
    clean_name = (name or "").strip()
    if not clean_name or len(clean_name) > MAX_NAME_LENGTH:
        raise ValidationError("Each field needs a name of 1 to 120 characters.")
    code = (country or "").strip().upper()
    if not COUNTRY_RE.match(code):
        raise ValidationError("Choose the two-letter country of the field (ES, FR, DE…).")
    points = [[round(float(p[1]), COORDINATE_DECIMALS), round(float(p[0]), COORDINATE_DECIMALS)]
              for p in outer_ring_lon_lat]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    if not MIN_POINTS <= len(points) <= MAX_POINTS:
        raise ValidationError(f"A field needs between {MIN_POINTS} and {MAX_POINTS} vertices.")
    identifier = field_id if field_id and field_id.startswith(DRAWN_PREFIX) else QGIS_ID_PREFIX + uuid.uuid4().hex
    payload: dict[str, Any] = {"id": identifier, "name": clean_name, "country": code, "polygon": points}
    if crop_code.strip():
        payload["crop_code"] = crop_code.strip()
    return payload
