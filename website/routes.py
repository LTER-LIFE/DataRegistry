#!/usr/bin/python
# Title: routes.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
import geoalchemy2.elements
from flask import Blueprint, render_template, flash, request
from lxml import etree
from . import db
from .forms import AddStudy
import folium
from folium.plugins import MousePosition, Draw, MarkerCluster
from folium.plugins.treelayercontrol import TreeLayerControl
from folium.features import Marker
import streamlit as st
from streamlit_folium import st_folium
from .models import Catalog
from geoalchemy2.elements import WKBElement
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO
from shapely import geometry as SHAPE_geo

# Define blueprint
homepage = Blueprint('homepage', __name__, template_folder='templates')

# Create the homepage route decorator
@homepage.route('/')
def home():
    main_map = folium.Map(location=(51.921485, 4.491922), zoom_start=15)
    marker_cluster = MarkerCluster().add_to(main_map)
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

    iframe = main_map.get_root()._repr_html_()

    return render_template('index.html', iframe=iframe)

@homepage.route('/add_study', methods=['GET','POST'])
def add_study():
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
                             collect_year=form.collect_year.data,
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

    return render_template('add_record.html', form=form)

@homepage.route('/search')
def search():
    return "<h1> Search page </h1>"

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
            return render_template('index.html')

    return render_template('add_xml.html')
