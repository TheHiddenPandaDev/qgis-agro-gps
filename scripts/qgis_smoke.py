from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsMapRendererParallelJob,
    QgsMapSettings,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path(os.environ.get("SMOKE_OUT", ROOT / "docs"))
SIZE = QSize(1200, 800)
NEIGHBOURS = [(41.6015, -4.0030), (41.5990, -4.0035)]


def render(layers, extent, path: Path) -> None:
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    settings.setExtent(extent)
    settings.setOutputSize(SIZE)
    settings.setBackgroundColor(QColor("white"))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    job.renderedImage().save(str(path), "PNG")


def main() -> int:
    profile = tempfile.mkdtemp(prefix="agro_gps_smoke_")
    app = QgsApplication([], True, profile)
    app.initQgis()
    from qgis.testing.mocked import get_iface

    from agro_gps import classFactory, layers
    from agro_gps.core.client import sigpac_parcel_at
    from agro_gps.core.export import field_payload
    from agro_gps.core.parsing import fields_from_records, sigpac_from_feature
    from agro_gps.qgis_transport import qgis_transport

    iface = get_iface()
    plugin = classFactory(iface)
    plugin.initGui()
    project = QgsProject.instance()
    assert not project.mapLayers()
    plugin.action.setChecked(True)
    assert plugin.dock is not None
    opened = list(project.mapLayers().values())
    assert len(opened) == 1 and opened[0].customProperty(layers.BASEMAP_MARKER), opened
    assert project.crs().authid() == "EPSG:3857"
    empty_extent = iface.mapCanvas().extent()
    assert empty_extent.width() > 1_000_000, empty_extent
    from agro_gps.core.presentation import start_extent
    spain = layers.frame(project, None, QgsRectangle(*start_extent("es_ES")))
    render(opened, spain, OUT / "empty-project.png")
    plugin.dock.prepare_view()
    assert len(project.mapLayers()) == 1

    neighbours = [sigpac_from_feature(sigpac_parcel_at(qgis_transport, lat, lon)) for lat, lon in NEIGHBOURS]
    records = [{"kind": "parcel", "id": f"DRAWN-{i}", "payload": {
        "name": f"Parcela {i + 1}", "country": "ES", "surface_ha": p.area_ha,
        "polygon": [[y, x] for x, y in p.rings[0]]}} for i, p in enumerate(neighbours)]
    field_layer = layers.fields_layer(project)
    count = layers.replace_fields(field_layer, fields_from_records(records))
    assert count == len(NEIGHBOURS), count
    assert layers.fields_layer(project) is field_layer

    feature = sigpac_parcel_at(qgis_transport, 41.6, -4.0)
    parcel = sigpac_from_feature(feature)
    assert parcel is not None and parcel.reference, parcel
    sigpac = layers.sigpac_layer(project)
    added = layers.add_sigpac(sigpac, parcel)
    basemap = layers.owned_layer(project, layers.BASEMAP_MARKER)
    assert basemap is not None and basemap.isValid()
    assert layers.ensure_basemap(project) is None
    assert not layers.prepare_empty_project(project, None, added.geometry().boundingBox())

    extent = layers.frame(project, None, added.geometry().boundingBox().buffered(0.004))
    render([field_layer, sigpac, basemap], extent, OUT / "map.png")
    plugin.dock.resize(380, 760)
    plugin.dock.status.setText(f"{parcel.reference} · {parcel.land_use} · {parcel.area_ha:.2f} ha")
    plugin.dock.grab().save(str(OUT / "panel.png"), "PNG")

    utm = QgsVectorLayer("Polygon?crs=EPSG:25830", "drawn", "memory")
    drawn = QgsFeature(utm.fields())
    drawn.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(361000, 4606000), QgsPointXY(361200, 4606000),
                                                  QgsPointXY(361200, 4606150), QgsPointXY(361000, 4606000)]]))
    ring = layers.outer_ring_lon_lat(drawn.geometry(), utm.crs(), project)
    payload = field_payload("Dibujada en QGIS", "ES", ring)
    assert 41 < payload["polygon"][0][0] < 42 and -5 < payload["polygon"][0][1] < -3, payload

    plugin.unload()
    result = {"qgis": app.applicationVersion() if hasattr(app, "applicationVersion") else "",
              "fields": count, "sigpac": parcel.reference, "land_use": parcel.land_use, "export": payload["polygon"][:2]}
    print(json.dumps(result))
    app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
