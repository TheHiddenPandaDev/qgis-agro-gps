from __future__ import annotations

import configparser
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "agro_gps"


def metadata():
    parser = configparser.ConfigParser()
    parser.read(PLUGIN / "metadata.txt", encoding="utf-8")
    return parser["general"]


def test_metadata_has_the_required_keys_and_qgis4_support():
    general = metadata()
    for key in ("name", "qgisMinimumVersion", "description", "about", "version", "author", "email", "repository",
                "tracker"):
        assert general.get(key), key
    assert general["qgisMaximumVersion"] == "4.99"
    assert "external service" in general["about"]


def test_version_matches_the_client_user_agent():
    from agro_gps.core.client import PLUGIN_VERSION

    assert metadata()["version"] == PLUGIN_VERSION


def test_plugin_files_exist():
    for name in ("__init__.py", "icon.png", "LICENSE", "metadata.txt"):
        assert (PLUGIN / name).exists(), name


def test_no_urllib_request_in_the_plugin():
    for path in PLUGIN.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "urllib.request" not in text and "urlopen" not in text, path
