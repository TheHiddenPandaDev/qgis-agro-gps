from __future__ import annotations

import pytest

from agro_gps.core.keys import AGRO, CATASTRO, EMPTY, UNKNOWN, key_kind
from agro_gps.core.presentation import default_name_field, fields_extent
from agro_gps.core.translations import SPANISH, language_of, translate


@pytest.mark.parametrize("credential, kind", [
    ("agk_b8629279687ecbd8", AGRO),
    ("  agk_abc  ", AGRO),
    ("pk_live_0123456789abcdef", CATASTRO),
    ("pk_test_0123456789abcdef", CATASTRO),
    ("sk_something", UNKNOWN),
    ("", EMPTY),
    ("   ", EMPTY),
    (None, EMPTY),
])
def test_key_kind(credential, kind):
    assert key_kind(credential) == kind


def test_fields_extent_spans_every_ring_of_every_field():
    first = [[(-0.15, 40.14), (-0.14, 40.14), (-0.14, 40.15), (-0.15, 40.14)]]
    second = [[(-3.95, 39.80), (-3.94, 39.80), (-3.94, 39.81), (-3.95, 39.80)],
              [(-3.946, 39.802), (-3.945, 39.802), (-3.945, 39.803), (-3.946, 39.802)]]
    assert fields_extent([first, second]) == (-3.95, 39.80, -0.14, 40.15)


def test_fields_extent_of_nothing_is_none():
    assert fields_extent([]) is None
    assert fields_extent([[]]) is None


@pytest.mark.parametrize("names, expected", [
    (["field_id", "name", "crop_code"], "name"),
    (["ID", "Nombre", "Area"], "Nombre"),
    (["fid", "REFCAT"], "REFCAT"),
    (["fid", "label", "ref"], "label"),
    (["fid", "area"], ""),
    ([], ""),
])
def test_default_name_field(names, expected):
    assert default_name_field(names) == expected


@pytest.mark.parametrize("locale, expected", [("es_ES", "es"), ("ca-ES", "ca"), ("EN_gb", "en"), ("", "")])
def test_language_of(locale, expected):
    assert language_of(locale) == expected


def test_translate_to_spanish_and_falls_back_to_english():
    assert translate("Pick a point on the map", "es_ES") == "Elegir un punto en el mapa"
    assert translate("Pick a point on the map", "gl_ES") == "Elegir un punto en el mapa"
    assert translate("Pick a point on the map", "de_DE") == "Pick a point on the map"
    assert translate("Not in the catalogue", "es_ES") == "Not in the catalogue"


def test_catastro_key_message_in_spanish():
    message = "This key is from Catastro GPS. Create an Agro GPS key in Agro GPS > Settings > API and webhooks."
    assert translate(message, "es") == "Esta clave es de Catastro GPS; crea una de Agro GPS en Ajustes > API y webhooks."


def test_spanish_placeholders_match_the_english_ones():
    import re
    for english, spanish in SPANISH.items():
        assert set(re.findall(r"{\w+}", english)) == set(re.findall(r"{\w+}", spanish)), english
