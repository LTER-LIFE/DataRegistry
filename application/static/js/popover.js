$(document).ready(function () {
    $('#spatial_covarage').click(function() {
        selectGeoLoc = $('#select-geo-loc');
        selectGeoLoc.toggleClass('hidden');
        if (selectGeoLoc.hasClass('hidden')) {
            console.log('map is hidden')
        } else {
            loadMap("osm");
        };
    });
});

var markers = new Array();

function createWktFromGeoJSON(geoJSONString, e) {
  var wkt_options = {};
  var geojson_format = new ol.format.GeoJSON();
  var layerFeatures = geojson_format.readFeatures(geoJSONString);
  var wkt_format = new ol.format.WKT(wkt_options);
  return wkt_format.writeFeatures(layerFeatures);
}

function createGeoJSONFromWkt(wktString) {
        var wkt_options = {};
        var geojson_format = new ol.format.GeoJSON();

        var wkt_format = new ol.format.WKT(wkt_options);
        var stringFeatures = wkt_format.readFeatures(wktString, {});
        return geojson_format.writeFeatures(stringFeatures);
}

function loadMap(osm) {
    // remove map if it already exists
    var container = L.DomUtil.get('select-geo-loc');
      if(container != null){
        container._leaflet_id = null;
      }


    var osmUrl='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    var osmAttribution='© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    var esriUrl='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
	var esriAttribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community';

    var osm = new L.TileLayer(osmUrl, {minZoom:2, maxZoom:19, attribution:osmAttribution});
    var esri = new L.TileLayer(esriUrl, {minZoom:2, maxZoom:19, attribution:esriAttribution});

    var map = new L.Map('select-geo-loc', { doubleClickZoom:false,
        zoomControl:true,
        maxBounds:([[90,-270],[-90,270]]),
        selectArea: true
        });
    osm.addTo(map)

    // container for address search results
    const addressSearchResults = new L.LayerGroup().addTo(map);

    // OSM Geocoder
    const osmGeocoder = new L.Control.geocoder({
        collapsed: false,
        position: 'topright',
        text: 'Search',
        placeholder: 'Search',
        defaultMarkGeocode: false
    }).addTo(map);

    // handle geocoding result event
    osmGeocoder.on('markgeocode', e => {
       // coordinates for result
       const coords = [e.geocode.center.lat, e.geocode.center.lng];
       // center map on result
       map.setView(coords, 16);
    });

    var map_set = "osm";
    map.fitBounds([[53,5],[50,6]]);

    // Add Layercontrol
        var baseMaps = {
        "OpenStreetMap": osm,
        "Esri Sattelite": esri
    };
    var layerControl = L.control.layers(baseMaps).addTo(map);

    var editableLayers = new L.FeatureGroup();
    map.addLayer(editableLayers);

    var drawControl = new L.Control.Draw({
      position: 'topright',
      draw: {
        polyline: true,
        polygon: {
          allowIntersection: false, // Restricts shapes to simple polygons
          drawError: {
            color: '#e1e100', // Color the shape will turn when intersects
            message: '<strong>Oh snap!<strong> you can\'t draw that!' // Message that will show when intersect
          }
        },
        circle: false, // not supported in geojson yet
        circlemarker: false, // not supported in geojson yet
        rectangle: true,
        marker: true
      },
      edit: {
        featureGroup: editableLayers, //REQUIRED!!
        remove: true
      }
    });

    map.addControl(drawControl);

    wkt_string = document.getElementById("spatial_covarage").value;
    if (wkt_string !== "") {
         // Replace old coordinates by wkt string
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

        geoJson = JSON.parse(createGeoJSONFromWkt(wkt_string));
        if (geoJson.type !== undefined) {
            $('#geographic_origin').val(wkt_string);
            geoJsonLayer = L.geoJSON(geoJson);
            geoJsonLayer.addTo(editableLayers);
            if (geoJsonLayer.getBounds().isValid()) {
                var bounds = geoJsonLayer.getBounds()
                map.fitBounds(bounds, {padding: [10]});

            };
        }
    }

    map.on(L.Draw.Event.CREATED, function(e) {
        var type = e.layerType,
        layer = e.layer;

        if (type === 'marker') {
            layer.bindPopup('LatLng: ' + layer.getLatLng().lat + ',' + layer.getLatLng().lng).openPopup();
        }

        editableLayers.addLayer(layer);

        layerGeoJSON = editableLayers.toGeoJSON();
        var out = createWktFromGeoJSON(layerGeoJSON);

        document.getElementById("spatial_covarage").value = out;

    });

    //On Draw Edit Event
    map.on(L.Draw.Event.EDITED, function(e) {
        var type = e.layerType,
        layer = e.layer;

        layerGeoJSON = editableLayers.toGeoJSON();
        var out = createWktFromGeoJSON(layerGeoJSON);

        document.getElementById("spatial_covarage").value = out;
        //$('#select-geo-loc').addClass("hidden");
    });

    //On Draw Delete Event
    map.on(L.Draw.Event.DELETED, function(e) {
        var type = e.layerType, layer = e.layer;

        layerGeoJSON = editableLayers.toGeoJSON();
        var out = createWktFromGeoJSON(layerGeoJSON);

        document.getElementById("spatial_covarage").value = out;

    });
}
