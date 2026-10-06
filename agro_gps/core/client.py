from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from .errors import AgroGpsError, NetworkError, ValidationError, error_from_response
from .transport import HttpResponse, Transport, TransportFailure, TransportTimeout

DEFAULT_BASE_URL = "https://api.agrogps.eu"
SIGPAC_POINT_URL = ("https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfobypoint/4258/"
                    "{lng:.7f}/{lat:.7f}.geojson")
DEFAULT_TIMEOUT_SECONDS = 30.0
HTTP_OK_MIN = 200
HTTP_OK_MAX = 299
PLUGIN_VERSION = "0.1.1"
USER_AGENT = f"agro-gps-qgis/{PLUGIN_VERSION}"
MAX_PAGES = 200
MAX_FIELDS_PER_IMPORT = 50
CREDENTIAL_HEADER = "X-API-Key"


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_point(lat: float, lng: float) -> bool:
    return _finite(lat) and _finite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180


class AgroGpsClient:
    def __init__(self, credential: str, *, transport: Transport, base_url: str = DEFAULT_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        secret = (credential or "").strip()
        if not secret:
            raise ValidationError("Paste your Agro GPS key first.", code="NO_KEY")
        self._secret = secret
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    def __repr__(self) -> str:
        return f"AgroGpsClient(base_url={self._base_url!r}, credential='***')"

    def farms(self) -> list[dict[str, Any]]:
        data = self._call("GET", "/api/v1/farms")
        farms = data if isinstance(data, list) else (data or {}).get("farms", [])
        return [f for f in farms if isinstance(f, dict) and f.get("id")]

    def parcel_records(self, farm_id: str) -> list[dict[str, Any]]:
        since = 0
        records: dict[str, dict[str, Any]] = {}
        for _ in range(MAX_PAGES):
            data = self._call("GET", "/api/v1/sync/records", {"farm_id": farm_id, "since": since}) or {}
            for record in data.get("records") or []:
                if isinstance(record, dict) and record.get("kind") == "parcel" and record.get("id"):
                    records[str(record["id"])] = record
            since = int(data.get("next") or since)
            if not data.get("has_more"):
                break
        return [r for r in records.values() if not r.get("deleted")]

    def import_fields(self, farm_id: str, fields: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if not fields:
            raise ValidationError("Select at least one polygon.")
        if len(fields) > MAX_FIELDS_PER_IMPORT:
            raise ValidationError(f"Send at most {MAX_FIELDS_PER_IMPORT} fields at a time.")
        data = self._call("POST", "/api/v1/fields", body={"farm_id": farm_id, "fields": list(fields)}) or {}
        return list(data.get("fields") or [])

    def _call(self, method: str, path: str, query: Mapping[str, Any] | None = None,
              body: Mapping[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {CREDENTIAL_HEADER: self._secret, "Accept": "application/json", "User-Agent": USER_AGENT}
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")
        response = _send(self._transport, method, url, headers, payload, self._timeout)
        return _data(response)


def sigpac_parcel_at(transport: Transport, lat: float, lng: float, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict:
    if not valid_point(lat, lng):
        raise ValidationError("Latitude and longitude must be valid WGS84 numbers.")
    url = SIGPAC_POINT_URL.format(lat=lat, lng=lng)
    response = _send(transport, "GET", url, {"Accept": "application/json", "User-Agent": USER_AGENT}, None, timeout)
    if not HTTP_OK_MIN <= response.status <= HTTP_OK_MAX:
        raise error_from_response(response)
    try:
        body = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise AgroGpsError("SIGPAC answered with something that is not GeoJSON.") from error
    features = body.get("features") if isinstance(body, dict) else None
    if not features:
        raise AgroGpsError("No SIGPAC parcel at that point (SIGPAC only covers Spain).", code="NO_PARCEL")
    return features[0]


def _send(transport: Transport, method: str, url: str, headers: Mapping[str, str], payload: bytes | None,
          timeout: float) -> HttpResponse:
    try:
        return transport(method, url, headers, payload, timeout)
    except TransportTimeout as error:
        raise NetworkError("The request timed out; try again.", code="TIMEOUT") from error
    except TransportFailure as error:
        raise NetworkError(f"No connection: {error}", code="NETWORK") from error


def _data(response: HttpResponse) -> Any:
    if not HTTP_OK_MIN <= response.status <= HTTP_OK_MAX:
        raise error_from_response(response)
    try:
        body = json.loads(response.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError) as error:
        raise AgroGpsError("Agro GPS answered with something that is not JSON.") from error
    return body.get("data") if isinstance(body, dict) else None
