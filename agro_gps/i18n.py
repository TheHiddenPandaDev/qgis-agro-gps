from __future__ import annotations

from qgis.PyQt.QtCore import QCoreApplication

CONTEXT = "AgroGps"


def tr(text: str) -> str:
    return QCoreApplication.translate(CONTEXT, text)
