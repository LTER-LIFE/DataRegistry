function createSimpleMap(containerId) {
    const container = L.DomUtil.get(containerId);
    if (container && container._leaflet_id) {
        L.map(container).remove();
    }
    const osm = new L.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        minZoom: 2, maxZoom: 19, attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    const esri = new L.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        minZoom: 2, maxZoom: 19, attribution: 'Tiles &copy; Esri...'
    });
    const map = new L.Map(containerId, {
        doubleClickZoom: false, zoomControl: true, maxBounds: [[90, -270], [-90, 270]]
    });
    map.setView([0, 0], 2);
    osm.addTo(map);
    const baseMaps = { "OpenStreetMap": osm, "Esri Satellite": esri };
    L.control.layers(baseMaps).addTo(map);
    return map;
}

// Step 2: The function that loads the GeoJSON data onto the map.
// This function should be called for each dataset with the GeoJSON data.
function loadDatasetMapWithGeoJSON(datasetId, geoJson) {
    const mapContainerId = 'geo-' + datasetId;

    const map = createSimpleMap(mapContainerId);

    if (geoJson && Object.keys(geoJson).length > 0) {
        const geoJsonLayer = L.geoJSON(geoJson);
        geoJsonLayer.addTo(map);
        const bounds = geoJsonLayer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, {
                padding: [10, 10]
            });
        }
    }
}