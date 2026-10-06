from __future__ import annotations

from collections.abc import Iterable

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsMapLayer,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsVectorTileLayer,
)
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor, QFont

from .core.parsing import Field, SigpacParcel
from .core.presentation import (
    FIELDS_COLOR,
    LABEL_COLOR,
    LABEL_HALO_COLOR,
    LABEL_HALO_OPACITY,
    LABEL_HALO_SIZE_MM,
    LABEL_MAX_SCALE_DENOMINATOR,
    LABEL_SIZE_PT,
    SATELLITE_ATTRIBUTION,
    SATELLITE_NAME,
    SIGPAC_COLOR,
    LayerInfo,
    fill_properties,
    has_basemap,
    label_expression,
    outline_properties,
    padded_extent,
    satellite_uri,
)

FIELDS_LAYER_NAME = "Agro GPS – fields"
SIGPAC_LAYER_NAME = "SIGPAC parcels"
FIELDS_MARKER = "agro_gps/fields"
SIGPAC_MARKER = "agro_gps/sigpac"
BASEMAP_MARKER = "agro_gps/basemap"
WGS84 = "EPSG:4326"
WEB_MERCATOR = "EPSG:3857"
MINIMUM_HALF_SIZE_METRES = 45.0
MINIMUM_HALF_SIZE_DEGREES = 0.0004
FIELDS_SCHEMA = (("field_id", QMetaType.Type.QString), ("name", QMetaType.Type.QString),
                 ("crop_code", QMetaType.Type.QString), ("country", QMetaType.Type.QString),
                 ("area_ha", QMetaType.Type.Double))
SIGPAC_SCHEMA = (("name", QMetaType.Type.QString), ("land_use", QMetaType.Type.QString),
                 ("area_ha", QMetaType.Type.Double), ("slope_pct", QMetaType.Type.Double),
                 ("irrigation", QMetaType.Type.Double))


def _owned(project: QgsProject, marker: str) -> QgsVectorLayer | None:
    for layer in project.mapLayers().values():
        if layer.customProperty(marker) and isinstance(layer, QgsVectorLayer):
            return layer
    return None


def _new_layer(project: QgsProject, name: str, marker: str, schema, color: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"Polygon?crs={WGS84}", name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField(field_name, kind) for field_name, kind in schema])
    layer.updateFields()
    layer.setCustomProperty(marker, True)
    _style(layer, color)
    project.addMapLayer(layer, False)
    project.layerTreeRoot().insertLayer(0, layer)
    return layer


def _style(layer: QgsVectorLayer, color: str) -> None:
    symbol = QgsFillSymbol()
    symbol.deleteSymbolLayer(0)
    symbol.appendSymbolLayer(QgsSimpleFillSymbolLayer.create(fill_properties(color)))
    for properties in outline_properties(color):
        symbol.appendSymbolLayer(QgsSimpleLineSymbolLayer.create(properties))
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    settings = QgsPalLayerSettings()
    settings.fieldName = label_expression("name", "area_ha")
    settings.isExpression = True
    text = QgsTextFormat()
    font = QFont()
    font.setBold(True)
    text.setFont(font)
    text.setSize(LABEL_SIZE_PT)
    text.setColor(QColor(LABEL_COLOR))
    halo = QgsTextBufferSettings()
    halo.setEnabled(True)
    halo.setSize(LABEL_HALO_SIZE_MM)
    halo.setColor(QColor(LABEL_HALO_COLOR))
    halo.setOpacity(LABEL_HALO_OPACITY)
    text.setBuffer(halo)
    settings.setFormat(text)
    settings.scaleVisibility = True
    settings.minimumScale = LABEL_MAX_SCALE_DENOMINATOR
    settings.maximumScale = 0
    placement = getattr(Qgis, "LabelPlacement", None)
    if placement is not None:
        settings.placement = placement.OverPoint
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def _polygon(rings) -> QgsGeometry:
    return QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in ring] for ring in rings])


def fields_layer(project: QgsProject) -> QgsVectorLayer:
    existing = _owned(project, FIELDS_MARKER)
    return existing or _new_layer(project, FIELDS_LAYER_NAME, FIELDS_MARKER, FIELDS_SCHEMA, FIELDS_COLOR)


def sigpac_layer(project: QgsProject) -> QgsVectorLayer:
    existing = _owned(project, SIGPAC_MARKER)
    return existing or _new_layer(project, SIGPAC_LAYER_NAME, SIGPAC_MARKER, SIGPAC_SCHEMA, SIGPAC_COLOR)


def replace_fields(layer: QgsVectorLayer, fields: Iterable[Field]) -> int:
    provider = layer.dataProvider()
    provider.truncate()
    features = []
    for field in fields:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(_polygon(field.rings))
        feature.setAttributes([field.field_id, field.name, field.crop_code, field.country, field.area_ha])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    layer.triggerRepaint()
    return len(features)


def add_sigpac(layer: QgsVectorLayer, parcel: SigpacParcel) -> QgsFeature:
    feature = QgsFeature(layer.fields())
    feature.setGeometry(_polygon(parcel.rings))
    feature.setAttributes([parcel.reference, parcel.land_use, parcel.area_ha, parcel.slope, parcel.irrigation])
    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()
    layer.triggerRepaint()
    return feature


def _infos(project: QgsProject) -> list[LayerInfo]:
    infos = []
    for layer in project.mapLayers().values():
        kind = "raster" if isinstance(layer, QgsRasterLayer) else "vectortile" if isinstance(
            layer, QgsVectorTileLayer) else "vector"
        infos.append(LayerInfo(kind, layer.providerType() or ""))
    return infos


def ensure_basemap(project: QgsProject) -> QgsRasterLayer | None:
    if has_basemap(_infos(project)):
        return None
    layer = QgsRasterLayer(satellite_uri(), SATELLITE_NAME, "wms")
    if not layer.isValid():
        return None
    metadata = layer.metadata()
    metadata.setRights([SATELLITE_ATTRIBUTION])
    layer.setMetadata(metadata)
    layer.setCustomProperty(BASEMAP_MARKER, True)
    project.addMapLayer(layer, False)
    project.layerTreeRoot().addLayer(layer)
    return layer


def frame(project: QgsProject, canvas, extent_wgs84: QgsRectangle) -> QgsRectangle:
    crs = QgsCoordinateReferenceSystem(WEB_MERCATOR)
    project.setCrs(crs)
    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(WGS84), crs, project)
    target = transform.transformBoundingBox(extent_wgs84)
    rectangle = QgsRectangle(*padded_extent(target.xMinimum(), target.yMinimum(), target.xMaximum(),
                                            target.yMaximum(), MINIMUM_HALF_SIZE_METRES))
    if canvas is not None:
        canvas.setDestinationCrs(crs)
        canvas.setExtent(rectangle)
        canvas.refresh()
    return rectangle


def outer_ring_lon_lat(geometry: QgsGeometry, source_crs: QgsCoordinateReferenceSystem,
                       project: QgsProject) -> list[tuple[float, float]]:
    geometry = QgsGeometry(geometry)
    if source_crs.authid() != WGS84:
        geometry.transform(QgsCoordinateTransform(source_crs, QgsCoordinateReferenceSystem(WGS84), project))
    if geometry.isMultipart():
        parts = geometry.asMultiPolygon()
        ring = max(parts, key=lambda p: QgsGeometry.fromPolygonXY(p).area())[0] if parts else []
    else:
        polygon = geometry.asPolygon()
        ring = polygon[0] if polygon else []
    return [(point.x(), point.y()) for point in ring]


def owned_layer(project: QgsProject, marker: str) -> QgsMapLayer | None:
    return _owned(project, marker)
