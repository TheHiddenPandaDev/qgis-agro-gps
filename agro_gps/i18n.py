from __future__ import annotations

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QCoreApplication, QLocale

from .core.translations import translate

CONTEXT = "AgroGps"
LOCALE_SETTING = "locale/userLocale"


def current_locale() -> str:
    return str(QgsSettings().value(LOCALE_SETTING, "") or QLocale().name())


def tr(text: str) -> str:
    translated = QCoreApplication.translate(CONTEXT, text)
    if translated != text:
        return translated
    return translate(text, current_locale())
