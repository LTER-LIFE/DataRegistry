#!/usr/bin/python
# Title: routes.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Blueprint, render_template, flash

from . import db
from .forms import AddStudy
import folium
from folium.plugins import MousePosition, Draw, MarkerCluster
from folium.plugins.treelayercontrol import TreeLayerControl
from folium.features import Marker
import streamlit as st
from streamlit_folium import st_folium
from .models import Catalog

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
        form.collect_year.data = ''
        form.keywords.data = ''
        form.polygon_location.data = ''

    return render_template('add_record.html', form=form)

@homepage.route('/search')
def search():
    return "<h1> Search page </h1>"
