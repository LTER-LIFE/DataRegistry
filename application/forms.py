#!/usr/bin/python
# Title: forms.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
import re
from datetime import datetime, timedelta

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, RadioField
from wtforms.fields.simple import SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, AnyOf, ValidationError
from wtforms.widgets import DateInput

from application.models import Dataset, Agent, Location, LicenseDocument, Keyword


def parse_times(iso_time_string):
    """
    Because datetime.fromisotime does not work with the following three ISO standard times
    This helper function tries to do that.
     - Reduced precision dates are not currently supported (YYYY-MM, YYYY).
     - Extended date representations are not currently supported (±YYYYYY-MM-DD).
     - Ordinal dates are not currently supported (YYYY-OOO).

    """
    try:
        return datetime.fromisoformat(iso_time_string)
    except ValueError as e:
        if re.search(r"[0-2][0-9][0-9][0-9]-[0-1][0-9]", iso_time_string):
            return datetime.strptime(iso_time_string, "%Y-%m")
        if re.search(r"[0-2][0-9][0-9][0-9]", iso_time_string):
            return datetime.strptime(iso_time_string, "%Y")
        if re.search(r"[0-2][0-9][0-9][0-9]-[0-3][0-9][0-9]", iso_time_string):
            print("Ordinal date is fully not supported yet, pick year")
            return datetime.strptime(iso_time_string[:4], "%Y")


class DatasetForm(FlaskForm):
    # Metadata provider
    metadata_provider_name = StringField("Name", validators=[DataRequired()], description="Your first and last name.")
    metadata_provider_organisation = StringField("Organisation name", validators=[],
                                                 description="The name of the organisation you are affiliated with.")
    metadata_provider_mbox = StringField("Email address", validators=[],
                                         description="This email address may serve as a point of contact for "
                                                     "LTER-LIFE in case there are questions about the metadata form "
                                                     "you are currently submitting. NB: by providing this email "
                                                     "address, you give consent to LTER-LIFE to display the email "
                                                     "address on the Veluwe Metadata Portal.")

    # Creator
    creator_name = StringField("Name", validators=[],
                               description="If the creator of the dataset is a person, please provide their first and "
                                           "last name.")
    creator_organisation = StringField("Organisation name", validators=[DataRequired()],
                                       description="If the creator of the dataset is an "
                                                   "organisation, provide the name of the "
                                                   "organisation here. - If the creator of the "
                                                   "dataset is a person, provide the name of the "
                                                   "organisation they are affiliated with.")
    creator_mbox = StringField("Email address", description="If the creator of the dataset is a person, please "
                                                            "provide their email address. NB: by providing this email "
                                                            "address, you give consent to LTER-LIFE to display the "
                                                            "email address on the Veluwe Metadata Portal. ")

    # Contact point
    dataset_contact_point_name = StringField("Name", validators=[DataRequired()],
                                             description="If the contact point of the dataset is a person, please "
                                                         "provide their first and last name. - If the contact point "
                                                         "of the dataset is a position, please provide their role.")
    dataset_contact_point_organisation = StringField("Organisation name", validators=[],
                                                     description="The name of the organisation the contact point is "
                                                                 "affiliated with.")
    dataset_contact_point_mbox = StringField("Email address", validators=[DataRequired()],
                                             description="This email address may serve as a point of contact for "
                                                         "users of the Veluwe Metadata Portal in case they have "
                                                         "questions about the dataset. NB: by providing this email "
                                                         "address, you give consent to LTER-LIFE to display the email "
                                                         "address on the Veluwe Metadata Portal. ")

    title = StringField("Title", validators=[DataRequired()], description="A brief description of the dataset. "
                                                                          "Recommended to include: subject, location,"
                                                                          " time period. ")
    description = TextAreaField("Description", validators=[DataRequired()],
                                description="A description of the contents of the dataset. The description will be "
                                            "used by full-text searches, and it should be rich with descriptive text. "
                                            "Multiple paragraphs may be included. It should contain enough "
                                            "information to allow potential data users to understand the data and "
                                            "decide on its fitness for use. In particular, descriptions should "
                                            "include information that does not fit into structured metadata, "
                                            "and focus on the “what”, “when”, and “where” information, "
                                            "general taxonomic information, as well as whether the data package is "
                                            "ongoing or completed. Some general methods description is appropriate, "
                                            "and broad classes of measured parameters should also be included.")

    keywords = StringField("Keywords", description="Commonly used words or "
                                                                                "phrases to describe the "
                                                                                "dataset. Format: separate "
                                                                                "keywords by a comma.")

    resource_type = StringField("Resource type", validators=[DataRequired()],
                                description="The nature of the dataset. Examples include but are not limited to: "
                                            "observational data, experimental data, remotely sensed data, sounds, "
                                            "images.")

    license = StringField("License", description="The license determines what rights may be available to "
                                                 "users when using the dataset. Recommend use: choose one of "
                                                 "the Creative Commons licenses. Examples include but are not "
                                                 "limited to: CC0, CC-BY, CC-BY-NC. Please see "
                                                 "https://creativecommons.org/share-your-work/cclicenses/ for "
                                                 "more Creative Commons licenses.")
    access_rights = StringField("Access rights", validators=[DataRequired()],
                                description="Information that indicates how the dataset can be accessed. Recommended "
                                            "use: choose one of: 1) open access, 2) restricted access, "
                                            "3) closed access. For definitions of these terms, "
                                            "check: http://purl.org/eprint/accessRights/.")

    publisher = StringField("Publisher name", validators=[],
                            description="The organisation that made a citable version of the dataset available "
                                        "online. Examples include but are not limited to: GBIF, Dataverse NL, Zenodo, "
                                        "Dryad, Figshare. ")

    public_id = StringField("Dataset ID", validators=[], description="DOI or other unique identifier "
                                                                        "associated with the published "
                                                                        "dataset.")

    landing_page = StringField("Landing page", validators=[], description="The web page (URL) that can be "
                                                                                    "navigated to in a web browser to "
                                                                                    "gain access to the dataset.")

    temporal_coverage_start = StringField("Start date", validators=[DataRequired()],
                                          description="The period of time when the data collection started. Format: "
                                                      "either YYYY or YYYY-MM-DD.")
    temporal_coverage_end = StringField("End date", validators=[DataRequired()],
                                        description="The period of time when the data collection ended. NB: If data "
                                                    "collection is ongoing, please select the latest period of time "
                                                    "that is included in the current version of the dataset. Format: "
                                                    "either YYYY or YYYY-MM-DD.")

    temporal_resolution = StringField("Temporal resolution", validators=[],
                                      description="The temporal resolution of the dataset is the frequency with which "
                                                  "data is collected or acquired. ")

    spatial_covarage = StringField("Spatial coverage", validators=[DataRequired()],
                                   description="The spatial extent that is covered by the dataset. Use the interactive "
                                               "map to draw the study area of your dataset.")

    spatial_resolution = StringField("Spatial resolution", description="If the dataset contains data acquired over a "
                                                                       "range of spatial locations during each "
                                                                       "collection period, document the spatial "
                                                                       "resolution of the dataset.")

    taxonomic_coverage = StringField("Taxonomic coverage", description="If applicable, taxonomic coverage is "
                                                                       "a description of the taxa represented "
                                                                       "in the dataset. May be as generic as "
                                                                       "'small passerines' or as specific as "
                                                                       "listing taxon names.")

    release_date = StringField("Metadata submission date", description="Date of registration of your dataset in the "
                                                                       "Veluwe Metadata Portal.",
                               validators=[DataRequired()])
    language = SelectField("Language", choices=[('EN', 'English'), ('NL', 'Nederlands')], validators=[DataRequired()],
                           description="Language used in this form")

    consent = RadioField("Terms and conditions", choices=[('Y', 'Yes')],
                         validators=[AnyOf(["Y"], message="Please answer Yes to proceed")],
                           description="I have read and agree to the terms and conditions")

    # User

    # submit field
    submit_button = SubmitField('Submit dataset')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.release_date.data = datetime.strftime(datetime.now(), "%Y-%m-%d")

    def clean(self):
        # Reset the form
        self.creator_name.data = ''
        self.creator_organisation.data = ''
        self.creator_mbox.data = ''

        self.dataset_contact_point_name.data = ''
        self.dataset_contact_point_organisation.data = ''
        self.dataset_contact_point_mbox.data = ''

        self.metadata_provider_name.data = ''
        self.metadata_provider_organisation.data = ''
        self.metadata_provider_mbox.data = ''

        self.release_date.data = ''
        self.language.data = ''
        self.title.data = ''
        self.description.data = ''
        self.resource_type.data = ''
        self.publisher.data = ''
        self.public_id.data = ''
        self.landing_page.data = ''
        self.temporal_coverage_start.data = ''
        self.temporal_coverage_end.data = ''
        self.temporal_resolution.data = ''
        self.spatial_covarage.data = ''
        self.spatial_resolution.data = ''
        self.license.data = ''
        self.access_rights.data = ''

    def to_dataset(self):
        dataset = Dataset()
        dataset.modified = datetime.now()
        dataset.release_date = parse_times(self.release_date.data)
        dataset.language = self.language.data
        dataset.title = self.title.data
        dataset.description = self.description.data
        dataset.resource_type = self.resource_type.data
        dataset.temporal_coverage_start = parse_times(self.temporal_coverage_start.data)
        dataset.temporal_coverage_end = parse_times(self.temporal_coverage_end.data)
        dataset.temporal_resolution = self.temporal_resolution.data
        dataset.spatial_resolution = self.spatial_resolution.data
        dataset.taxonomic_coverage = self.taxonomic_coverage.data
        dataset.access_rights = self.access_rights.data
        dataset.landing_page = self.landing_page.data
        dataset.public_id = self.public_id.data


        # Fill creator -> Agent
        dataset.creator = Agent.add_or_update_agent(name=self.creator_name.data,
                                                    organisation=self.creator_organisation.data,
                                                    mbox=self.creator_mbox.data)
        # dataset_contact_point -> Agent
        dataset.dataset_contact_point = Agent.add_or_update_agent(name=self.dataset_contact_point_name.data,
                                                                  organisation=self.dataset_contact_point_organisation.data,
                                                                  mbox=self.dataset_contact_point_mbox.data)

        # dataset_contact_point -> Agent
        dataset.dataset_metadata_provider = Agent.add_or_update_agent(name=self.metadata_provider_name.data,
                                                              mbox=self.metadata_provider_mbox.data,
                                                              organisation=self.metadata_provider_organisation.data)

        # publisher -> Agent
        dataset.publisher = Agent.add_or_update_agent(organisation=self.publisher.data)

        dataset.dataset_keywords = Keyword.add_or_update_keywords(keyword_names=self.keywords.data)

        # spatial_covarage -> Location
        # db_location = Location.add_or_update_location(geometry=self.spatial_covarage.data)
        dataset.dataset_spatial_covarage = Location.add_or_update_location(geometry=self.spatial_covarage.data)

        # licence -> LicenceDocument
        dataset.dataset_license = LicenseDocument(label=self.license.data)

        return dataset


