function Load_BaseMap() {
    var map = L.map('map').setView([52.075919, 5.891922],8)

    var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    osm.addTo(map);

    // Tile map layers


    googleStreets = L.tileLayer('http://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',{
    maxZoom: 20,
    subdomains:['mt0','mt1','mt2','mt3']
    });
    googleStreets.addTo(map);

    googleSat = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',{
    maxZoom: 20,
    subdomains:['mt0','mt1','mt2','mt3']
    });
    googleSat.addTo(map);

// Layer control
    var baseLayers ={
      "Google Streets": googleStreets,
      "Google Satellite": googleSat,
      "Open StreetMap": osm
    };
    L.control.layers(baseLayers).addTo(map);


}
