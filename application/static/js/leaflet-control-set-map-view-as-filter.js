export function setMapViewAsFilterControl(opts) {
    return new L.Control.SetMapViewAsFilter(opts)
}

L.Control.SetMapViewAsFilter = L.Control.extend({
    onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control')

        this.button = L.DomUtil.create(
            'a',
            'leaflet-control-button w-auto px-2',
            container
        )

        this.button.innerHTML = 'Set map view as Area filter'
        this.button.role = 'button'

        L.DomEvent.disableClickPropagation(this.button);

        L.DomEvent.on(this.button, 'click', () => {
            this._updateAreaFilter(map)
        })

        container.title = "Set the map view as an Area filter"

        return container
    },

    onRemove: function() {
        L.DomEvent.off(this.button, 'click', L.DomEvent.stop)
    },

    // create a counter-clockwise WKT Polygon
    _boundsToWkt: function(bounds) {
        return 'POLYGON((' +
            `${bounds.getWest()} ${bounds.getNorth()},` +
            `${bounds.getWest()} ${bounds.getSouth()},` +
            `${bounds.getEast()} ${bounds.getSouth()},` +
            `${bounds.getEast()} ${bounds.getNorth()},` +
            `${bounds.getWest()} ${bounds.getNorth()}` +
        '))'
    },

    _updateAreaFilter: function (map) {
        const areaFilter = $('#spatial_coverage')
        const inputMap = $('#input-map')
        const wkt = this._boundsToWkt(map.getBounds())

        areaFilter.val(wkt)

        // show popover map if it is not visible
        if (inputMap.hasClass("visually-hidden")) {
            $('select[name="area"] option[id=area-custom]')
                .prop("selected", true)

            inputMap.removeClass('visually-hidden')

            initInputByMap()
        } else {
            // otherwise redraw the wkt on the popover map
            loadMapContent(mapInstance, editableLayers)
        }

        // refresh search results
        areaFilter.trigger('change')
    }
})
