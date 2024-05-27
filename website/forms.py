#!/usr/bin/python
# Title: forms.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Blueprint, render_template
from flask_wtf import FlaskForm
from wtforms import SearchField, StringField, SubmitField, FieldList
from wtforms.validators import DataRequired

# Create Form class add_study
class AddStudy(FlaskForm):
    # title of a dataset
    title = StringField("Dataset name", validators=[DataRequired()])
    # describe the dataset
    description = StringField("Description of the dataset", validators=[DataRequired()])
    # email
    contact = StringField("Contact person", validators=[DataRequired()])
    # data location
    data_location = StringField("Hyperlink to the dataset")
    # later change to foreignkey institute
    institute = StringField("Institute of the dataset", validators=[
        DataRequired()])
    keywords = FieldList(StringField("Description of the dataset", validators=[
        DataRequired()],
                         min_entries=1))
    # location flag
    flag_location = StringField("Coordinates", validators=[DataRequired()])
    # polygon
    polygon_location = StringField("Polyogon of the dataset")
    # submit field
    submit_butt = SubmitField('Submit dataset')
