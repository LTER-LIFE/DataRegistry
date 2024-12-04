function createGeoJSONFromWkt(wktString) {
        var wkt_options = {};
        var geojson_format = new ol.format.GeoJSON();

        var wkt_format = new ol.format.WKT(wkt_options);
        var stringFeatures = wkt_format.readFeatures(wktString, {});
        return geojson_format.writeFeatures(stringFeatures);
};

function loadDatasetMap(datasetId, wkt_string) {
    var osmUrl='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    var osmAttribution='© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    var esriUrl='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
	var esriAttribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community';

    var osm = new L.TileLayer(osmUrl, {minZoom:2, maxZoom:19, attribution:osmAttribution});
    var esri = new L.TileLayer(esriUrl, {minZoom:2, maxZoom:19, attribution:esriAttribution});


    var map = new L.Map('geo-' + datasetId, { doubleClickZoom:false,
        zoomControl:true,
        maxBounds:([[90,-270],[-90,270]]),
        selectArea: true
        });
    osm.addTo(map)
    var map_set = "osm";

    // Replace old coordinates by new
    let single_regex = /^[+-]?\d+.\d+, [+-]?\d+.\d+/g;
    // (51.15437, 11.85132), (49.89729, 15.10448)
    let block_regex = /^\([+-]?\d+.\d+, [+-]?\d+.\d+\), \([+-]?\d+.\d+, [+-]?\d+.\d+\)/g;

    if (single_regex.test(wkt_string)) {
        const coords = wkt_string.split(", ");
        wkt_string = "POINT("+ coords[1] + " " + coords[0] + ")"
    } else if (block_regex.test(wkt_string)) {
        wkt_string = wkt_string.replace(/[()]/gi, "");
        const coords = wkt_string.split(", ");
        wkt_string = `POLYGON((${coords[1]} ${coords[2]}, ${coords[1]} ${coords[0]}, ${coords[3]} ${coords[0]}, ${coords[3]} ${coords[2]}, ${coords[1]} ${coords[2]}))`
    } else if (wkt_string === "None") {
        wkt_string = "GEOMETRYCOLLECTION EMPTY"
    }

    // Add Layercontrol
    var baseMaps = {
        "OpenStreetMap": osm,
        "Esri Sattelite": esri
    };
    var layerControl = L.control.layers(baseMaps).addTo(map);

    geoJson = JSON.parse(createGeoJSONFromWkt(wkt_string));
    if (geoJson.type !== undefined) {
        geoJsonLayer = L.geoJSON(geoJson);
        geoJsonLayer.addTo(map);
        if (geoJsonLayer.getBounds().isValid()) {
            map.fitBounds(geoJsonLayer.getBounds());
            map.setZoom(8);
        };
    }


}
