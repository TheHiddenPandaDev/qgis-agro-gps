from __future__ import annotations

from collections.abc import Mapping

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from .core.transport import HttpResponse, TransportFailure, TransportTimeout

MILLISECONDS = 1000


def qgis_transport(method: str, url: str, headers: Mapping[str, str], body: bytes | None,
                   timeout: float) -> HttpResponse:
    request = QNetworkRequest(QUrl(url))
    for name, value in headers.items():
        request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))
    if hasattr(request, "setTransferTimeout"):
        request.setTransferTimeout(int(timeout * MILLISECONDS))
    blocking = QgsBlockingNetworkRequest()
    if method == "POST":
        outcome = blocking.post(request, QByteArray(body or b""), True)
    else:
        outcome = blocking.get(request, True)
    reply = blocking.reply()
    status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
    if status is not None and int(status) > 0:
        return HttpResponse(int(status), bytes(reply.content()))
    if outcome == QgsBlockingNetworkRequest.ErrorCode.TimeoutError:
        raise TransportTimeout(blocking.errorMessage())
    raise TransportFailure(blocking.errorMessage() or "Network request failed")
