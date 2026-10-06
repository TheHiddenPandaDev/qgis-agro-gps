from __future__ import annotations

from qgis.core import QgsSettings

CREDENTIAL_SETTING = "agro_gps/credential"
FARM_SETTING = "agro_gps/farm"
COUNTRY_SETTING = "agro_gps/country"


def _text(path: str) -> str:
    return str(QgsSettings().value(path, "") or "").strip()


def _store(path: str, value: str) -> None:
    settings = QgsSettings()
    if value.strip():
        settings.setValue(path, value.strip())
    else:
        settings.remove(path)


def load_credential() -> str:
    return _text(CREDENTIAL_SETTING)


def save_credential(value: str) -> None:
    _store(CREDENTIAL_SETTING, value)


def load_farm() -> str:
    return _text(FARM_SETTING)


def save_farm(value: str) -> None:
    _store(FARM_SETTING, value)


def load_country() -> str:
    return _text(COUNTRY_SETTING) or "ES"


def save_country(value: str) -> None:
    _store(COUNTRY_SETTING, value.upper())
