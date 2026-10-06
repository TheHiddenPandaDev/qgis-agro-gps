from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

MIN_RING_POINTS = 3
SIGPAC_KEY_PARTS = ("provincia", "municipio", "agregado", "zona", "poligono", "parcela", "recinto")


@dataclass(frozen=True)
class Field:
    field_id: str
    name: str
    crop_code: str
    country: str
    area_ha: float | None
    rings: list[list[tuple[float, float]]]


@dataclass(frozen=True)
class SigpacParcel:
    reference: str
    land_use: str
    area_ha: float | None
    slope: float | None
    irrigation: float | None
    rings: list[list[tuple[float, float]]]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _ring_from_lat_lng(points: Any) -> list[tuple[float, float]]:
    ring: list[tuple[float, float]] = []
    if not isinstance(points, list):
        return ring
    for point in points:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            lat, lng = _number(point[0]), _number(point[1])
            if lat is not None and lng is not None:
                ring.append((lng, lat))
    return ring


def _closed(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if ring and ring[0] != ring[-1]:
        return ring + [ring[0]]
    return ring


def field_from_record(record: dict[str, Any]) -> Field | None:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    ring = _ring_from_lat_lng(payload.get("polygon"))
    if len(ring) < MIN_RING_POINTS:
        return None
    field_id = str(record.get("id") or payload.get("refcat") or "")
    return Field(
        field_id=field_id,
        name=str(payload.get("name") or field_id),
        crop_code=str(payload.get("crop_code") or ""),
        country=str(payload.get("country") or ""),
        area_ha=_number(payload.get("surface_ha")),
        rings=[_closed(ring)],
    )


def fields_from_records(records: Sequence[dict[str, Any]]) -> list[Field]:
    fields = [field_from_record(r) for r in records]
    return sorted((f for f in fields if f is not None), key=lambda f: f.name.lower())


def _geojson_rings(geometry: Any) -> list[list[tuple[float, float]]]:
    if not isinstance(geometry, dict):
        return []
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    polygons = [coordinates] if kind == "Polygon" else coordinates if kind == "MultiPolygon" else []
    rings: list[list[tuple[float, float]]] = []
    for polygon in polygons:
        for ring in polygon or []:
            points = [(float(p[0]), float(p[1])) for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
            if len(points) >= MIN_RING_POINTS:
                rings.append(_closed(points))
    return rings


def sigpac_reference(properties: dict[str, Any]) -> str:
    return ":".join(str(properties.get(part, "")) for part in SIGPAC_KEY_PARTS)


def sigpac_from_feature(feature: dict[str, Any]) -> SigpacParcel | None:
    properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    rings = _geojson_rings(feature.get("geometry"))
    if not rings:
        return None
    return SigpacParcel(
        reference=sigpac_reference(properties),
        land_use=str(properties.get("uso_sigpac") or ""),
        area_ha=_number(properties.get("superficie")),
        slope=_number(properties.get("pendiente_media")),
        irrigation=_number(properties.get("coef_regadio")),
        rings=rings,
    )
