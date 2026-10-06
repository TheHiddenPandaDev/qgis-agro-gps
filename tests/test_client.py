from __future__ import annotations

import json

import pytest
from conftest import SECRET, FakeTransport, json_response

from agro_gps.core.client import CREDENTIAL_HEADER, AgroGpsClient, sigpac_parcel_at, valid_point
from agro_gps.core.errors import (
    AgroGpsError,
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ReadOnlyKeyError,
    ServerError,
    ValidationError,
)
from agro_gps.core.transport import HttpResponse, TransportFailure, TransportTimeout

FARM = "11111111-1111-1111-1111-111111111111"


def client(*responses):
    transport = FakeTransport(*responses)
    return AgroGpsClient(SECRET, transport=transport, base_url="https://api.test/"), transport


def test_requires_a_key_and_hides_it():
    with pytest.raises(ValidationError):
        AgroGpsClient("  ", transport=FakeTransport())
    c, _ = client()
    assert SECRET not in repr(c)


def test_farms_sends_the_key_and_returns_the_list():
    c, t = client(json_response(200, {"data": [{"id": FARM, "name": "Finca"}, {"name": "no id"}]}))
    assert c.farms() == [{"id": FARM, "name": "Finca"}]
    assert t.calls[0]["url"] == "https://api.test/api/v1/farms"
    assert t.calls[0]["headers"][CREDENTIAL_HEADER] == SECRET
    assert t.calls[0]["method"] == "GET"


def test_farms_accepts_an_object_envelope():
    c, _ = client(json_response(200, {"data": {"farms": [{"id": FARM}]}}))
    assert c.farms() == [{"id": FARM}]


def test_parcel_records_pages_and_keeps_last_state():
    first = {"data": {"records": [
        {"kind": "parcel", "id": "A", "payload": {"name": "a"}},
        {"kind": "worker", "id": "W"},
        {"kind": "parcel", "id": "B", "payload": {}},
        "junk",
    ], "next": 7, "has_more": True}}
    second = {"data": {"records": [{"kind": "parcel", "id": "B", "deleted": True}], "next": 9, "has_more": False}}
    c, t = client(json_response(200, first), json_response(200, second))
    assert [r["id"] for r in c.parcel_records(FARM)] == ["A"]
    assert "since=7" in t.calls[1]["url"]
    assert f"farm_id={FARM}" in t.calls[0]["url"]


def test_import_fields_posts_json():
    c, t = client(json_response(200, {"data": {"fields": [{"id": "DRAWN-x", "result": "accepted"}]}}))
    out = c.import_fields(FARM, [{"name": "N", "country": "ES", "polygon": [[1, 2], [1, 3], [2, 3]]}])
    assert out == [{"id": "DRAWN-x", "result": "accepted"}]
    call = t.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.test/api/v1/fields"
    assert call["headers"]["Content-Type"] == "application/json"
    assert json.loads(call["body"])["farm_id"] == FARM


def test_import_fields_validates_batch_size():
    c, _ = client()
    with pytest.raises(ValidationError):
        c.import_fields(FARM, [])
    with pytest.raises(ValidationError):
        c.import_fields(FARM, [{}] * 51)


@pytest.mark.parametrize("status,payload,error", [
    (401, {"code": "AUT_003", "message": "Clave de API no válida"}, AuthError),
    (403, {"code": "AUT_004"}, ReadOnlyKeyError),
    (403, {"code": "FIN_403"}, AuthError),
    (404, {}, NotFoundError),
    (429, {}, RateLimitError),
    (400, {"code": "FIN_400", "message": "Datos no válidos"}, ValidationError),
    (502, "not json", ServerError),
    (302, {}, AgroGpsError),
])
def test_errors_map_to_types(status, payload, error):
    body = payload if isinstance(payload, dict) else payload
    response = json_response(status, body) if isinstance(body, dict) else HttpResponse(status, body.encode())
    c, _ = client(response)
    with pytest.raises(error):
        c.farms()


def test_error_message_comes_from_the_api():
    c, _ = client(json_response(401, {"code": "AUT_003", "message": "Clave de API no válida"}))
    with pytest.raises(AuthError, match="Clave de API no válida") as info:
        c.farms()
    assert info.value.code == "AUT_003" and info.value.status == 401


def test_error_with_a_non_object_body():
    c, _ = client(HttpResponse(500, b"[1]"))
    with pytest.raises(ServerError):
        c.farms()


def test_bad_json_and_non_object_success():
    c, _ = client(HttpResponse(200, b"{oops"), HttpResponse(200, b"[]"))
    with pytest.raises(AgroGpsError, match="not JSON"):
        c.farms()
    assert c.farms() == []


@pytest.mark.parametrize("failure,code", [(TransportTimeout("slow"), "TIMEOUT"), (TransportFailure("dns"), "NETWORK")])
def test_transport_failures_become_network_errors(failure, code):
    c, _ = client(failure)
    with pytest.raises(NetworkError) as info:
        c.farms()
    assert info.value.code == code


def test_valid_point():
    assert valid_point(40.4, -3.7)
    assert not valid_point(91, 0)
    assert not valid_point(float("nan"), 0)
    assert not valid_point(True, 0)


def test_sigpac_parcel_at_returns_the_first_feature():
    feature = {"type": "Feature", "properties": {"uso_sigpac": "TA"}, "geometry": {}}
    t = FakeTransport(json_response(200, {"features": [feature]}))
    assert sigpac_parcel_at(t, 41.6, -4.0) == feature
    assert t.calls[0]["url"].endswith("/4258/-4.0000000/41.6000000.geojson")
    assert CREDENTIAL_HEADER not in t.calls[0]["headers"]


def test_sigpac_errors():
    with pytest.raises(ValidationError):
        sigpac_parcel_at(FakeTransport(), 200, 0)
    with pytest.raises(AgroGpsError, match="No SIGPAC parcel"):
        sigpac_parcel_at(FakeTransport(json_response(200, {"features": []})), 1, 1)
    with pytest.raises(AgroGpsError, match="not GeoJSON"):
        sigpac_parcel_at(FakeTransport(HttpResponse(200, b"<html>")), 1, 1)
    with pytest.raises(ServerError):
        sigpac_parcel_at(FakeTransport(HttpResponse(503, b"")), 1, 1)
    with pytest.raises(AgroGpsError, match="No SIGPAC parcel"):
        sigpac_parcel_at(FakeTransport(json_response(200, [1])), 1, 1)
