#!/usr/bin/python
# Title: forms.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Blueprint, render_template
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import SearchField, StringField, SubmitField, FieldList
from wtforms.fields.datetime import DateField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea
from flask_jwt_extended import jwt_required, get_jwt_identity
# Create Form class add_study
class AddStudy(FlaskForm):
    # title of a dataset
    title = StringField("Dataset name", validators=[DataRequired()])
    # describe the dataset
    description = StringField("Description of the dataset",
                              validators=[DataRequired()], widget=TextArea())
    # data owner
    contact = StringField("Contact person", validators=[DataRequired()])
    # email
    email = StringField("E-mail data owner", validators=[DataRequired()])
    # data location
    data_location = StringField("Hyperlink to the dataset")
    # later change to foreignkey institute
    institute = StringField("Institute", validators=[
        DataRequired()])
    # keywords
    keywords = StringField("Keywords ',' separated", validators=[
        DataRequired()])
    # collection year
    collect_year_start = DateField("Year start of data collection", validators=[
        DataRequired()])
    collect_year_end = DateField("Year end of data collection", validators=[
        DataRequired()])
    # polygon
    polygon_location = StringField("Polygon of the dataset", validators=[DataRequired()])
    # submit field
    submit_butt = SubmitField('Submit dataset')
