#!/usr/bin/python
# Title: forms.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from datetime import datetime, timedelta

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired
from wtforms.widgets import DateInput

from application.models import Dataset, Agent, Location, LicenseDocument


# Checkbox class


# Create Form class add_study
class DatasetForm(FlaskForm):
    ### LTER-LIFE subset
    release_date = DateField("Release date")
    language = SelectField("Language", choices=[('EN', 'English'), ('NL', 'Nederlands')],
                           validators=[DataRequired()])

    metadata_provider = StringField("Metadata provider", validators=[DataRequired()], description="The provider of the "
                                                                                          "metadata")
    creator = StringField("creator", validators=[DataRequired()])
    title = StringField("Dataset title", validators=[DataRequired()])
    description = StringField("Dataset description", validators=[DataRequired()])
    resource_type = StringField("resource type", validators=[DataRequired()])
    dataset_contact_point = StringField("Dataset contact point", validators=[DataRequired()])
    publisher = StringField("Dataset publisher", validators=[DataRequired()])

    temporal_coverage_start = DateField("Dataset start date", widget=DateInput(), validators=[DataRequired()])
    temporal_coverage_end = DateField("Dataset end date", widget=DateInput(), validators=[DataRequired()])
    temporal_resolution = StringField("Dataset temporal resolution", validators=[DataRequired()])

    spatial_covarage = StringField("Dataset spatial coverage", validators=[DataRequired()])
    spatial_resolution = StringField("Dataset spatialcoverage resolution", validators=[DataRequired()])

    taxonomic_coverage = StringField("Dataset taxonomic coverage", validators=[DataRequired()])

    license = StringField("Dataset licence", validators=[DataRequired()])
    access_rights = StringField("Dataset access rights", validators=[DataRequired()])




    # submit field
    submit_button = SubmitField('Submit dataset')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.release_date.data = datetime.now()

    def clean(self):
        # Reset the form
        self.release_date.data = ''
        self.language.data = ''
        self.creator.data = ''
        self.title.data = ''
        self.description.data = ''
        self.resource_type.data = ''
        self.dataset_contact_point.data = ''
        self.publisher.data = ''
        self.temporal_coverage_start.data = ''
        self.temporal_coverage_end.data = ''
        self.temporal_resolution.data = ''
        self.spatial_covarage.data = ''
        self.spatial_resolution.data = ''
        self.license.data = ''
        self.access_rights.data = ''
        self.metadata_provider.data = ''

    def to_dataset(self):
        dataset = Dataset()
        dataset.modified = datetime.now()
        dataset.release_date = self.release_date.data
        dataset.language = self.language.data
        dataset.title = self.title.data
        dataset.description = self.description.data
        dataset.resource_type = self.resource_type.data
        dataset.temporal_coverage_start = self.temporal_coverage_start.data
        dataset.temporal_coverage_end = self.temporal_coverage_end.data
        dataset.temporal_resolution = self.temporal_resolution.data
        dataset.spatial_resolution = self.spatial_resolution.data
        dataset.taxonomic_coverage = self.taxonomic_coverage.data
        dataset.access_rights = self.access_rights.data

        # Fill creator -> Agent
        dataset.creator = Agent.add_or_update_agent(mbox=self.creator.data)
        # dataset_contact_point -> Agent
        dataset.dataset_contact_point = Agent.add_or_update_agent(mbox=self.dataset_contact_point.data)
        # publisher -> Agent
        dataset.publisher = Agent.add_or_update_agent(mbox=self.publisher.data)

        metadata_provider = Agent.add_or_update_agent(mbox=self.metadata_provider.data)
        # keywords -> Keyword

        # spatial_covarage -> Location
        #db_location = Location.add_or_update_location(geometry=self.spatial_covarage.data)
        dataset.dataset_spatial_covarage = Location.add_or_update_location(geometry=self.spatial_covarage.data)

        # licence -> LicenceDocument
        dataset.license = LicenseDocument(code=self.license.data)

        return dataset

    def test_dataset(self):
        dataset = Dataset()
        dataset.modified = datetime.now()
        dataset.release_date = datetime.now()
        dataset.language = "EN"
        dataset.title = "Title of the mock dataset"
        dataset.description = "Description of the mock dataset"
        dataset.resource_type = "Resource type of the mock dataset"
        dataset.temporal_coverage_start = datetime.now() - timedelta(days=1)
        dataset.temporal_coverage_end = datetime.now() + timedelta(days=1)
        dataset.temporal_resolution = "1"
        dataset.spatial_resolution = "1"
        dataset.taxonomic_coverage = "Rabbit"
        dataset.access_rights = "OPEN"

        eric = "e.kuijt@nioo.knaw.nl"
        stefan = "s.vriend@nioo.knaw.nl"
        # Fill creator -> Agent
        dataset.creator = Agent.add_or_update_agent(eric)
        # dataset_contact_point -> Agent
        dataset.dataset_contact_point = Agent.add_or_update_agent(eric)
        # publisher -> Agent
        dataset.publisher = Agent.add_or_update_agent(stefan)

        # metadata_provider -> Agent
        dataset.metadata_provider = Agent.add_or_update_agent(stefan)
        # keywords -> Keyword

        # spatial_covarage -> Location
        # db_location = Location.add_or_update_location(geometry=self.spatial_covarage.data)
        dataset.dataset_spatial_covarage = Location.add_or_update_location(geometry="POINT(5.858043 52.028838)")

        # licence -> LicenceDocument
        dataset.license = LicenseDocument(code="CC-BY-4.0")

        return dataset



