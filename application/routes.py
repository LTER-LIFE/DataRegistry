import json
from collections import defaultdict

import shapely
from flask import render_template, Blueprint, flash
from flask import current_app as app
from geoalchemy2.functions import ST_AsGeoJSON

from application.database import db_session
from application.forms import DatasetForm
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location

# Blueprint Configuration
# Here the static folder and the templates folder are annotated
proxy_prefix = app.config.get("PROXY_PREFIX")
url_prefix = f"{proxy_prefix}/".replace("//", "/") if proxy_prefix else "/"

# Blueprint Configuration
main_bp = Blueprint("main_bp", __name__, template_folder="templates", static_folder="static", url_prefix=url_prefix)

@main_bp.route('/')
def home(dataset_id=None):
    datasets = db_session.query(Dataset).all()

    datasets_shapes = defaultdict(dict)
    for dataset in datasets:
        dataset_dict = {}
        dataset_dict["centroid"] = json.loads(dataset.dataset_spatial_covarage.to_shape(field="centroid", to="geojson"))
        dataset_dict["geometry"] = json.loads(dataset.dataset_spatial_covarage.to_shape(field="geometry", to="geojson"))
        dataset_dict["properties"] = {"id": dataset.title,
                                      "title": dataset.title,
                                      "description": dataset.description,
                                      "keywords": [kw.name for kw in dataset.dataset_keywords]}
        datasets_shapes[dataset.dataset_id] = dataset_dict

    return render_template('index.html', list_o_geo=datasets_shapes)

@main_bp.route('/add_dataset', methods=['GET', 'POST'])
def add_dataset():
    name = None
    dataset_form = DatasetForm()
    # Validate the add study form
    if dataset_form.validate_on_submit():
        dataset = dataset_form.to_dataset()
        # Add to the database
        db_session.add(dataset)
        # Commit study to the database
        db_session.commit()
        db_session.flush()
        # Feedback
        flash(("Entry '{}' is now being reviewed!").format(dataset.title))

    return render_template('dataset_form.html', form=dataset_form, name=name)

@main_bp.route('/datasets')
@main_bp.route('/S3cr3T/datasets')
def datasets(dataset_id=None):
    datasets = db_session.query(Dataset).all()

    datasets_shapes = []

    return render_template('dataset_table.html', datasets=datasets)