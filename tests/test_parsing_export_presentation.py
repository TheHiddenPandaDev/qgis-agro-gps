from __future__ import annotations

import pytest

from agro_gps.core.errors import ValidationError
from agro_gps.core.export import QGIS_ID_PREFIX, field_payload
from agro_gps.core.parsing import field_from_record, fields_from_records, sigpac_from_feature, sigpac_reference
from agro_gps.core.presentation import (
    LayerInfo,
    fill_properties,
    format_area,
    has_basemap,
    is_basemap,
    label_expression,
    outline_properties,
    padded_extent,
    rgba,
    satellite_uri,
)

SQUARE = [[40.0, -3.0], [40.0, -2.99], [40.01, -2.99], [40.01, -3.0]]


def test_field_from_record_swaps_to_lon_lat_and_closes_the_ring():
    record = {"id": "DRAWN-1", "payload": {"name": "Norte", "crop_code": "1", "country": "ES", "surface_ha": 94.8,
                                           "polygon": SQUARE}}
    field = field_from_record(record)
    assert field.name == "Norte" and field.crop_code == "1" and field.area_ha == 94.8
    assert field.rings[0][0] == (-3.0, 40.0)
    assert field.rings[0][0] == field.rings[0][-1]
    assert len(field.rings[0]) == 5


def test_field_without_outline_is_skipped_and_names_fall_back():
    assert field_from_record({"id": "X", "payload": {"polygon": [[1, 2]]}}) is None
    assert field_from_record({"id": "X", "payload": "bad"}) is None
    named = field_from_record({"id": "R1", "payload": {"polygon": SQUARE + [SQUARE[0]], "surface_ha": True}})
    assert named.name == "R1" and named.area_ha is None and len(named.rings[0]) == 5
    junk = field_from_record({"id": "J", "payload": {"polygon": [[1, "a"], "x", [1, 2], [2, 2], [2, 3]]}})
    assert len(junk.rings[0]) == 4
    assert field_from_record({"id": "N", "payload": {"polygon": "x"}}) is None


def test_fields_are_sorted_by_name():
    records = [{"id": "b", "payload": {"name": "beta", "polygon": SQUARE}},
               {"id": "a", "payload": {"name": "Alfa", "polygon": SQUARE}}, {"id": "c", "payload": {}}]
    assert [f.name for f in fields_from_records(records)] == ["Alfa", "beta"]


def test_sigpac_feature_parsing():
    feature = {"properties": {"provincia": 47, "municipio": 1, "agregado": 0, "zona": 0, "poligono": 2, "parcela": 3,
                              "recinto": 1, "superficie": 2.5, "uso_sigpac": "TA", "pendiente_media": 2.5,
                              "coef_regadio": None},
               "geometry": {"type": "Polygon", "coordinates": [[[-4.0, 41.6], [-4.01, 41.6], [-4.01, 41.61]]]}}
    parcel = sigpac_from_feature(feature)
    assert parcel.reference == "47:1:0:0:2:3:1"
    assert parcel.area_ha == 2.5 and parcel.land_use == "TA" and parcel.slope == 2.5 and parcel.irrigation is None
    assert parcel.rings[0][0] == parcel.rings[0][-1]
    multi = {"properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 0]]], [[[2, 2], [3, 2]]]]}}
    assert len(sigpac_from_feature(multi).rings) == 1
    assert sigpac_from_feature({"properties": {}, "geometry": {"type": "Point", "coordinates": [1, 2]}}) is None
    assert sigpac_from_feature({"geometry": None}) is None
    assert sigpac_reference({}) == "::::::"


def test_field_payload_converts_to_lat_lng_and_validates():
    ring = [(-3.0, 40.0), (-2.99, 40.0), (-2.99, 40.01), (-3.0, 40.0)]
    payload = field_payload("  Huerta ", "es", ring, crop_code=" 7 ")
    assert payload["name"] == "Huerta" and payload["country"] == "ES" and payload["crop_code"] == "7"
    assert payload["polygon"] == [[40.0, -3.0], [40.0, -2.99], [40.01, -2.99]]
    assert payload["id"].startswith(QGIS_ID_PREFIX)
    assert field_payload("a", "FR", ring, field_id="DRAWN-keep")["id"] == "DRAWN-keep"
    assert field_payload("a", "FR", ring, field_id="13077A")["id"].startswith(QGIS_ID_PREFIX)
    assert "crop_code" not in field_payload("a", "FR", ring)
    for name, country, points in (("", "ES", ring), ("x" * 121, "ES", ring), ("a", "ESP", ring), ("a", "E1", ring),
                                  ("a", "ES", ring[:2])):
        with pytest.raises(ValidationError):
            field_payload(name, country, points)


def test_presentation_helpers():
    assert format_area(None) == ""
    assert format_area(2.345) == "2.35 ha"
    assert format_area(0.25) == "2500 m²"
    assert rgba("#2f7d32", 64) == "47,125,50,64"
    assert fill_properties("#000000")["color"] == "0,0,0,64"
    assert len(outline_properties("#000000")) == 2
    assert satellite_uri().startswith("type=xyz&url=https://server.arcgisonline.com") and "%7Bz%7D" in satellite_uri()
    assert '"name"' in label_expression("name", "area_ha") and "ha" in label_expression("name", "area_ha")
    assert padded_extent(0, 0, 10, 10, 1) == (-1.5, -1.5, 11.5, 11.5)
    assert padded_extent(0, 0, 0, 0, 5) == (-5, -5, 5, 5)
    assert is_basemap(LayerInfo("raster", "gdal")) and is_basemap(LayerInfo("vector", "WMS"))
    assert not has_basemap([LayerInfo("vector", "memory")])
