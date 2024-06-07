import json
from ast import literal_eval

import branca.element
import folium
import psycopg2
from folium import Marker
from folium.plugins import MarkerCluster, MousePosition
from flask import Blueprint, jsonify, render_template, request
from flask_restful import Api
from marshmallow import ValidationError
from folium.plugins.treelayercontrol import TreeLayerControl
from sqlalchemy.dialects.postgresql import psycopg2

from website.models.db_data_loader import load_db_data
from website.resources.user import UserList, UserResource

# Set up the blueprints
homepage = Blueprint('homepage', __name__, url_prefix='/',
                      template_folder='templates')
app = Api(homepage)

app.add_resource(UserList, '/users')
app.add_resource(UserResource, '/users/<int:id>')


@homepage.errorhandler(ValidationError)
def validation_error(e):
    return jsonify(e.messages), 400


@homepage.route('/')
def home():
    """

    :return:
    """
    # TAG FILTER OPTION

    # base stuff
    main_map = folium.Map(location=(52.075919, 5.891922), zoom_start=12)

    # Add clustering of markers
    marker_cluster = MarkerCluster().add_to(main_map)

    # Create feature layer (feature: Area)
    area_fg = folium.features.FeatureGroup(name="Area", show=False).add_to(main_map)
    area_fg.add_to(marker_cluster)
    # LOADS the data to make generating the markers easier
    list_o_dicts = load_db_data()

    # hold the individual datapoints
    holding_list = []
    # Create the flags
    for key_id, values_id in list_o_dicts.items():
        print(values_id['title'])
        popup_html = f"""
        <head> <base target="_parent"> </head>
        <style> </style>
        <div class="textual adjust-order--vert">
        <h3 class="heading h2"> {values_id['title']}</h3>
        </div>
        <div class="description">{values_id['description']}</div>
        <div class="contact">Contact:   {values_id['contact_person']}</div>
        <div class="keywords">Keyword(s):   {values_id['keywords']}</div>
        <div class="start-collect">Start collect: {values_id['collect_year_start']}</div>
        <div class="start-collect">Stop collect:  {values_id['collect_year_end']}</div>
        """

        area_entry = folium.GeoJson(values_id['polygon'],
                           style_function=lambda feature: {
                               "fillColor": "#ffff00",
                               "color": "black",
                               "weight": 2,
                               "dashArray": "5, 5",
                           }
                           ).add_to(area_fg)
        # transform html popup into iframe
        iframe = branca.element.IFrame(html=popup_html, width=300, height=400)
        html_iframe = folium.Popup(iframe, max_width="100%")

        print(values_id['points'])
        # Makes a marker for each study
        marker_flag = Marker(literal_eval(values_id['points']),
                             popup=html_iframe,
                             tooltip="Click me").add_to(marker_cluster)

        entry_dict = {"label": values_id['title'],
                      "children": [
                          {"label": "Area", "layer": area_entry}
                      ]}
        holding_list.append(entry_dict)

    # Create feature group consisting of area belonging to study surrounding the marker
    feat_group_area = folium.features.FeatureGroup(name="Area",
                                                   show=False).add_to(main_map)

    overlay_filter = {
        "label": "Filters",
        "select_all_checkbox": "De/select All",
        "children": [
            {"label": "The Netherlands",
             "selectAllCheckbox": True,
             "children": holding_list}
        ]}

    # Define the main map dims
    main_map.get_root().width = "100%"
    main_map.get_root().height = "800px"
    # Format for the Coordinates
    format_coord = "function(num) { return L.Util.formatNum(num, 6)+ 'º ';};"
    # Mouse hover for coordinates
    MousePosition(
        position="topright",
        separator=" | ",
        empty_String="NaN",
        lng_first=True,
        num_digits=40,
        prefix="Coordinates:",
        lat_formatter=format_coord,
        lng_formatter=format_coord,
    ).add_to(main_map)
    # Add Filter overlay for Treestyle indentation of the filters to the map
    TreeLayerControl(overlay_tree=overlay_filter).add_to(main_map)

    iframe = main_map.get_root()._repr_html_()

    return render_template('index.html', iframe=iframe)


@homepage.route('/search')
def search():
    return "<h1>Search</h1>"


@homepage.route('/contact')
def contact():
    return "<h1>Contact</h1>"


@homepage.route('/about')
def about():
    return "<h1>About</h1>"


@homepage.route('/sign_in')
def sign_in():
    return "<h1>Sign In</h1>"
