import json
from ast import literal_eval

from flask_bcrypt import Bcrypt
from flask_login import current_user
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
from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_restful import Api
from marshmallow import ValidationError
from folium.plugins.treelayercontrol import TreeLayerControl
from sqlalchemy.dialects.postgresql import psycopg2
from werkzeug.utils import secure_filename
from extensions import db
from website import Catalog
from website.forms import AddStudy, UserForm
from website.models import User
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


@homepage.route('/contact')
def contact():
    return "<h1>Contact</h1>"


@homepage.route('/about')
def about():
    return "<h1>About</h1>"

@homepage.route('/table')
def table_view():
    pd_datatable = load_db_table()

    return render_template('table_view.html', datasets=[pd_datatable.to_html(
                                                       header='true', index=False,
        classes='table table-striped table-bordered' "id="'myTable')])

@homepage.route('/sign_in')
def sign_in():
    return "<h1>Sign In</h1>"


@homepage.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('/'))
    form_reg = UserForm()
    # if form_reg.validate_on_submit():
    #     hashed_password = bcrypt.generate_password_hash(
    #         form_reg.password_hash.data).decode('utf-8')


    return "<h1>Register</h1>"


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
