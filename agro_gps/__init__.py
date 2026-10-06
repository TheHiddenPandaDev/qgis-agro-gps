def classFactory(iface):
    from .plugin import AgroGpsPlugin

    return AgroGpsPlugin(iface)
