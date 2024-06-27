import json
from ast import literal_eval
from lxml import etree

import branca.element
import folium
import psycopg2
import shapely.geometry
from shapely import wkt
import pandas as pd
import geopandas as gpd
import shapely.geometry as SHAPE_geo
from shapely.geometry import MultiPoint, Point, Polygon, shape
from folium import Marker
from folium.plugins import MarkerCluster, MousePosition, GroupedLayerControl
from flask import Blueprint, jsonify, render_template, request, flash
from flask_restful import Api
from marshmallow import ValidationError
from folium.plugins.treelayercontrol import TreeLayerControl
from sqlalchemy.dialects.postgresql import psycopg2
from werkzeug.utils import secure_filename

from extensions import db
from website import Catalog
from website.forms import AddStudy
from website.models.db_data_loader import load_db_data, load_db_table
from website.resources.user import UserList, UserResource

# Set up the blueprints
homepage = Blueprint('homepage', __name__, url_prefix='/',
                      template_folder='templates')
app = Api(homepage)

app.add_resource(UserList, '/users')
app.add_resource(UserResource, '/users/<int:id>')


icon_create_function = """\
function(cluster) {
    return L.divIcon({
    html: '<b>' + cluster.getChildCount() + '</b>',
    className: 'marker-cluster marker-cluster-large',
    iconSize: new L.Point(20, 20)
    });
}"""



@homepage.errorhandler(ValidationError)
def validation_error(e):
    return jsonify(e.messages), 400


# @homepage.route('/')
# def home():
#     """
#
#     :return:
#     """
#     # TAG FILTER OPTION
#
#     # base stuff
#     main_map = folium.Map(location=(52.075919, 5.891922), zoom_start=12)
#     # map esri
#     tile_esri = folium.TileLayer(
#         tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
#         attr='Esri',
#         name='Esri Satellite',
#         overlay=False,
#         control=True
#     ).add_to(main_map)
#     # map streets
#     street_map= folium.TileLayer('openstreetmap').add_to(main_map)
#
#     GroupedLayerControl(groups={
#         'Maps': [tile_esri, street_map]},
#         collapsed=False).add_to(main_map)
#     # add map layers
#
#
#     # Add clustering of markers
#     marker_cluster = MarkerCluster().add_to(main_map)
#
#     # Create feature layer (feature: Area)
#     area_fg = folium.features.FeatureGroup(name="Area", show=False).add_to(main_map)
#     # area_fg.add_to(marker_cluster)
#     # LOADS the data to make generating the markers easier
#     list_o_dicts, data_json = load_db_data()
#     print(list_o_dicts)
#     print(data_json)
#     # hold the individual datapoints
#     holding_list = []
#     # Create the flags
#     for key_id, values_id in list_o_dicts.items():
#         print(values_id['title'])
#         popup_html = f"""
#         <head> <base target="_parent"> </head>
#         <style> </style>
#         <div class="textual adjust-order--vert">
#         <h3 class="heading h2"> {values_id['title']}</h3>
#         </div>
#         <div class="description">{values_id['description']}</div>
#         <div class="contact">Contact:   {values_id['contact_person']}</div>
#         <div class="keywords">Keyword(s):   {values_id['keywords']}</div>
#         <div class="start-collect">Start collect: {values_id['collect_year_start']}</div>
#         <div class="start-collect">Stop collect:  {values_id['collect_year_end']}</div>
#         """
#
#         area_entry = folium.GeoJson(values_id['polygon'],
#                            style_function=lambda feature: {
#                                "fillColor": "#ffff00",
#                                "color": "black",
#                                "weight": 2,
#                                "dashArray": "5, 5",
#                            }
#                            ).add_to(area_fg)
#         # transform html popup into iframe
#         iframe = branca.element.IFrame(html=popup_html, width=300, height=400)
#         html_iframe = folium.Popup(iframe, max_width="100%")
#
#         # Markers
#         marker_cords_list =[]
#         for long, lat in literal_eval(values_id['markers'])['coordinates']:
#             print(lat, long)
#             print(type(lat), type(long))
#             coords = lat, long
#             marker_cords_list.append(coords)
#         # if there are multiple markers for a single study create them all
#         for k in range(0, len(marker_cords_list)):
#             marker = folium.Marker(marker_cords_list[k])
#             html_iframe = folium.Popup(iframe, max_width="100%")
#             html_iframe.add_to(marker)
#             marker_cluster.add_child(marker)
#
#         # Old method only creates a single marker
#         # Makes a marker for each study
#         #marker_flag = Marker(literal_eval(values_id['points']),
#         #                     popup=html_iframe,
#         #                     tooltip="Click me").add_to(marker_cluster)
#         #print(marker_flag)
#
#         entry_dict = {"label": values_id['title'],
#                       "children": [
#                           {"label": "Area", "layer": area_entry}
#                       ]}
#         holding_list.append(entry_dict)
#
#     # Create feature group consisting of area belonging to study surrounding the marker
#     feat_group_area = folium.features.FeatureGroup(name="Area",
#                                                    show=False).add_to(main_map)
#
#     overlay_filter = {
#         "label": "Filters",
#         "select_all_checkbox": "De/select All",
#         "children": [
#             {"label": "The Netherlands",
#              "selectAllCheckbox": True,
#              "children": holding_list}
#         ]}
#
#     # Define the main map dims
#     main_map.get_root().width = "100%"
#     main_map.get_root().height = "800px"
#     # Format for the Coordinates
#     format_coord = "function(num) { return L.Util.formatNum(num, 6)+ 'º ';};"
#     # Mouse hover for coordinates
#     MousePosition(
#         position="topright",
#         separator=" | ",
#         empty_String="NaN",
#         lng_first=True,
#         num_digits=40,
#         prefix="Coordinates:",
#         lat_formatter=format_coord,
#         lng_formatter=format_coord,
#     ).add_to(main_map)
#
#     # Add Filter overlay for Treestyle indentation of the filters to the map
#     TreeLayerControl(overlay_tree=overlay_filter).add_to(main_map)
#
#     iframe = main_map.get_root()._repr_html_()
#
#     return render_template('index.html', iframe=iframe)



@homepage.route('/contact')
def contact():
    return "<h1>Contact</h1>"


@homepage.route('/about')
def about():
    return "<h1>About</h1>"

@homepage.route('/table')
def table_view():
    data_table = load_db_table()

    print(data_table)


    return render_template('table_view.html',datasets=[data_table.to_html(
                                                       header= 'true')])


@homepage.route('/sign_in')
def sign_in():
    return "<h1>Sign In</h1>"

@homepage.route('add_study', methods=['GET', 'POST'])
def add_study():
    name = None
    form = AddStudy()
    # Validate the add study form
    if form.validate_on_submit():
        data_entry = Catalog(title=form.title.data,
                             description=form.description.data,
                             email=form.email.data,
                             contact_person=form.contact.data,
                             data_location=form.data_location.data,
                             institute=form.institute.data,
                             keywords=form.keywords.data,
                             collect_year_start=form.collect_year_start.data,
                             collect_year_end=form.collect_year_end.data,
                             polygon_location=form.polygon_location.data
                             )
        # Add to the database
        db.session.add(data_entry)
        # Commit study to the database
        db.session.commit()
        # Feedback
        flash(("Data '{}' added successfully!").format(data_entry.title))
        # Reset the form
        form.title.data = ''
        form.description.data = ''
        form.email.data = ''
        form.contact.data = ''
        form.data_location.data = ''
        form.institute.data = ''
        form.collect_year_start.data = ''
        form.collect_year_end.data = ''
        form.keywords.data = ''
        form.polygon_location.data = ''
    return render_template('add_record.html', form=form, name=name)

@homepage.route('/upload', methods=['GET', 'POST'])
def upload_xml():
    """

    :return:
    """

    if request.method == "POST":
        uploaded_xml = request.files.getlist("file")
        print(uploaded_xml)
        print("this is the uploaded xml" )
        for file in uploaded_xml:
            filename = secure_filename(file.filename)
            print(filename)
            if filename == "":
                flash("Please upload an XML file")
                return "No file selected"
            if filename.endswith(".xml"):
                # parsing
                single_entry_lines = etree.parse(file)



                # Find title
                for child in single_entry_lines.findall(".//title"):
                    title = child.text

                # Find abstract/ description
                for child in single_entry_lines.findall(".//abstract/para"):
                    description = child.text

                # Find email
                for child in single_entry_lines.findall(
                        ".//metadataProvider/electronicMailAddress"):
                    email = child.text

                # Find contact surname
                for child in single_entry_lines.findall(
                        ".//metadataProvider/individualName/surName"):
                    contact_surname = child.text
                # Find contact name
                for child in single_entry_lines.findall(
                        ".//metadataProvider/individualName/givenName"):
                    contact_name = child.text
                # Combine the name to get contact_person
                contact_person = contact_surname + "," + contact_name

                # Online/hyperlink
                for child in single_entry_lines.findall(".//onlineUrl"):
                    data_location = child.text

                # Institute
                for child in single_entry_lines.findall(".//organizationName"):
                    institute = child.text

                # Keywords
                keywords_list = []
                for child in single_entry_lines.findall(".//keyword"):
                    keywords_list.append(child.text)
                keywords = ", ".join(keywords_list)

                # Collection start year
                for child in single_entry_lines.findall(".//beginDate/calendarDate"):
                    start_date = child.text
                # Collection end year
                for child in single_entry_lines.findall(".//endDate/calendarDate"):
                    end_date = child.text

                # Location geographic
                for child in single_entry_lines.findall(".//westBoundingCoordinate"):
                    west_coord = child.text
                for child in single_entry_lines.findall(".//eastBoundingCoordinate"):
                    east_coord = child.text
                for child in single_entry_lines.findall(".//northBoundingCoordinate"):
                    north_coord = child.text
                for child in single_entry_lines.findall(".//southBoundingCoordinate"):
                    south_coord = child.text

                poly_col = SHAPE_geo.Polygon(((west_coord, north_coord), (west_coord,
                                                                 south_coord),
                                   (east_coord, south_coord), (east_coord, north_coord)))
                pol_center = poly_col.centroid
                polygon_location = 'GEOMETRYCOLLECTION({},{})'.format(
                    poly_col, pol_center)

                # Combine into data entry
                entry = Catalog(title=title,
                                description=description,
                                contact_person=contact_person,
                                email=email,
                                data_location=data_location,
                                institute=institute,
                                keywords=keywords,
                                collect_year_start=start_date,
                                collect_year_end=end_date,
                                polygon_location=polygon_location
                                )
                # commit to database
                db.session.add(entry)
                db.session.commit()
                flash("Xml data added successfully!")
            else:
                pass


    return render_template('add_xml.html')

@homepage.route('/')
def home():
    data_json= load_db_data()
    print(type(data_json))
    print(json.dumps(data_json, indent=4))
    return render_template('new_map.html', list_o_geo=json.dumps(data_json))
