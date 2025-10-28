/** Global variables to hold the map instance and its layers. */
let mapInstance = null;
let editableLayers = null;
let osmGeocoder = null;

$(document).ready(function() {
    /**
     * Handles the click event on the 'spatial_coverage' button.
     * Initializes the map on the first click and shows/hides it on subsequent clicks.
     */
    $('#spatial_coverage').click(function() {
        const selectGeoLoc = $('#select-geo-loc');
        selectGeoLoc.toggleClass('hidden');

        if (!selectGeoLoc.hasClass('hidden')) {
            if (mapInstance === null) {
                const mapAndLayers = initializeMap();
                mapInstance = mapAndLayers.map;
                editableLayers = mapAndLayers.editableLayers;

                // Attach event listeners for the Leaflet.draw controls.
                mapEvents();
            }

            // Always call invalidateSize() when the container is made visible
            mapInstance.invalidateSize();
            
            // Reload the dynamic map data and features
            loadMapContent(mapInstance, editableLayers);
        }
    });
});

// --- Core Functions ---

/**
 * Initializes the Leaflet map and its static controls.
 * This function should only be called once.
 * @returns {object} An object containing the map and editable layers.
 */
function initializeMap() {
    // Correctly remove an old map instance if it somehow exists
    const container = L.DomUtil.get('select-geo-loc');
    if (container && container._leaflet_id) {
        L.map(container).remove();
    }

    // Set up tile layers
    const osm = new L.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        minZoom: 2,
        maxZoom: 19,
        attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    const esri = new L.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        minZoom: 2,
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed...'
    });

    // Create the map instance
    const map = new L.Map('select-geo-loc', {
        doubleClickZoom: false,
        zoomControl: true,
        maxBounds: [
            [90, -270],
            [-90, 270]
        ],
        selectArea: true
    });

    // Set a default view for the map
    map.setView([52.0, 5.0], 5);

    osm.addTo(map);

    // Create the geocoder once and store it
    osmGeocoder = new L.Control.geocoder({
        collapsed: false,
        position: 'topright',
        text: 'Search',
        placeholder: 'Search',
        defaultMarkGeocode: false
    }).addTo(map);

    // Add map selector
    const baseMaps = { "OpenStreetMap": osm, "Esri Satellite": esri };
    L.control.layers(baseMaps).addTo(map);
    
    // Add draw controls and layers
    const editableLayers = new L.FeatureGroup().addTo(map);
    const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
            polyline: true,
            polygon: { allowIntersection: false, drawError: { color: '#e1e100', message: '<strong>Oh snap!</strong> you can\'t draw that!' } },
            rectangle: true,
            marker: false,
            circle: false,
            circlemarker: false,
        },
        edit: { featureGroup: editableLayers, remove: true }
    });
    map.addControl(drawControl);

    return { map: map, editableLayers: editableLayers };
}

/**
 * Loads dynamic content like WKT data onto the map.
 * This is the function that gets called repeatedly.
 * @param {L.Map} map - The Leaflet map instance.
 * @param {L.FeatureGroup} editableLayers - The layer to add features to.
 */
function loadMapContent(map, editableLayers) {
    editableLayers.clearLayers();

    const wkt_string = document.getElementById("spatial_coverage").value;
    if (wkt_string) {
        let single_regex = /^[+-]?\d+\.\d+, [+-]?\d+\.\d+/g;
        let block_regex = /^\([+-]?\d+\.\d+, [+-]?\d+\.\d+\), \([+-]?\d+\.\d+, [+-]?\d+\.\d+\)/g;

        let geoJsonString = null;
        if (single_regex.test(wkt_string)) {
            const coords = wkt_string.split(", ");
            const convertedWkt = `POINT(${coords[1]} ${coords[0]})`;
            geoJsonString = createGeoJSONFromWkt(convertedWkt);
        } else if (block_regex.test(wkt_string)) {
            const tempWkt = wkt_string.replace(/[()]/gi, "");
            const coords = tempWkt.split(", ");
            const convertedWkt = `POLYGON((${coords[1]} ${coords[2]}, ${coords[1]} ${coords[0]}, ${coords[3]} ${coords[0]}, ${coords[3]} ${coords[2]}, ${coords[1]} ${coords[2]}))`;
            geoJsonString = createGeoJSONFromWkt(convertedWkt);
        } else if (wkt_string === "None") {
            geoJsonString = createGeoJSONFromWkt("GEOMETRYCOLLECTION EMPTY");
        } else {
            geoJsonString = createGeoJSONFromWkt(wkt_string);
        }

        const geoJson = JSON.parse(geoJsonString);
        if (geoJson.type) {
            $('#geographic_origin').val(wkt_string);
            const geoJsonLayer = L.geoJSON(geoJson);
            geoJsonLayer.addTo(editableLayers);
            const bounds = geoJsonLayer.getBounds();
            
            if (boundsValid(bounds)) {
                map.fitBounds(bounds, { padding: [10] });
            }
        }
    }
}

/**
 * Sets up all the map's one-time event listeners.
 */
function mapEvents() {
    // This event handler needs to be attached to the map instance after it is created
    // A better way is to move this into the initializeMap function.
    // We will place it here for clarity, but you should move these to initializeMap().
    if(mapInstance) {
        mapInstance.on(L.Draw.Event.CREATED, function(e) {
            editableLayers.addLayer(e.layer);
            const layerGeoJSON = editableLayers.toGeoJSON();
            const wktOut = createWktFromGeoJSON(layerGeoJSON);
            document.getElementById("spatial_coverage").value = wktOut;
            $("#spatial_coverage").trigger('change');
        });

        mapInstance.on(L.Draw.Event.EDITED, function(e) {
            const layerGeoJSON = editableLayers.toGeoJSON();
            const wktOut = createWktFromGeoJSON(layerGeoJSON);
            document.getElementById("spatial_coverage").value = wktOut;
            $("#spatial_coverage").trigger('change');
        });

        mapInstance.on(L.Draw.Event.DELETED, function(e) {
            const layerGeoJSON = editableLayers.toGeoJSON();
            const wktOut = createWktFromGeoJSON(layerGeoJSON);
            document.getElementById("spatial_coverage").value = wktOut;
            $("#spatial_coverage").trigger('change');
        });
        
        osmGeocoder.on('markgeocode', e => {
            const coords = [e.geocode.center.lat, e.geocode.center.lng];
            mapInstance.setView(coords, 16);
        });
    }
}

// --- Utility Functions (Cleaned) ---

/**
 * Converts a GeoJSON string to WKT format using OpenLayers.
 */
function createWktFromGeoJSON(geoJSONString) {
    const geojson_format = new ol.format.GeoJSON();
    const layerFeatures = geojson_format.readFeatures(geoJSONString);
    const wkt_format = new ol.format.WKT();
    return wkt_format.writeFeatures(layerFeatures);
}

/**
 * Converts a WKT string to GeoJSON format using OpenLayers.
 */
function createGeoJSONFromWkt(wktString) {
    const geojson_format = new ol.format.GeoJSON();
    const wkt_format = new ol.format.WKT();
    const stringFeatures = wkt_format.readFeatures(wktString);
    return geojson_format.writeFeatures(stringFeatures);
}

/**
 * Checks if a Leaflet bounds object is valid and free of NaN values.
 */
function boundsValid(bounds) {
    if (!bounds || typeof bounds.getSouthWest !== 'function' || typeof bounds.getNorthEast !== 'function') {
        return false;
    }
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    if (isNaN(sw.lat) || isNaN(sw.lng) || isNaN(ne.lat) || isNaN(ne.lng)) {
        return false;
    }

    return bounds.isValid();
}