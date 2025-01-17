import json
from collections import defaultdict
from flask import render_template, Blueprint, flash, request, abort
from flask import current_app as app

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


TITLE = "Veluwe Metadata Portal (Beta)"
@main_bp.route('/')
def home(dataset_id=None):
    try:
        datasets = db_session.query(Dataset).all()

        datasets_shapes = defaultdict(dict)
        for dataset in datasets:
            dataset_dict = {}
            dataset_dict["centroid"] = json.loads(dataset.dataset_spatial_covarage.to_shape(field="centroid", to="geojson"))
            dataset_dict["geometry"] = json.loads(dataset.dataset_spatial_covarage.to_shape(field="geometry", to="geojson"))
            dataset_dict["properties"] = {"id": dataset.title,
                                          "title": dataset.title,
                                          "description": dataset.description,
                                          "creator": str(dataset.creator),
                                          "temporal_coverage": f"{dataset.temporal_coverage_start} / "
                                                           f"{dataset.temporal_coverage_end}"
                                          }
            datasets_shapes[dataset.dataset_id] = dataset_dict

        page = render_template('index.html', list_o_geo=datasets_shapes, title=TITLE)

    except Exception as e:
        abort(500, description="Failed to fetch datasets and render to map.", original_exception=e)

    return page


@main_bp.route('/S3cr3T/datasets/edit/<dataset_id>')
@main_bp.route('/S3cr3T/datasets/delete/<dataset_id>')
@main_bp.route('/add_dataset', methods=['GET', 'POST'])
def add_dataset(dataset_id=None):
    #
        name = None
        dataset_form = DatasetForm()
        # Validate the add study form
        if request.url_rule.rule.find("edit") > -1:
            dataset = Dataset.query.get(dataset_id)
            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            else:
                dataset_form.from_dataset(dataset)


        if request.url_rule.rule.find("delete") > -1:
            dataset = Dataset.query.get(dataset_id)
            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            db_session.delete(dataset)
            db_session.commit()
            db_session.flush()
            flash(f"Deleted dataset {dataset_id}", "success")

        if request.url_rule.rule.find("copy") > -1:
            pass
        if dataset_form.validate_on_submit():
            dataset = dataset_form.to_dataset()
            # Add to the database
            db_session.add(dataset)
            # Commit study to the database
            db_session.commit()
            db_session.flush()
            # Feedback
            flash(f"Added dataset with title {dataset.title}.", "success")

        page = render_template('dataset_form.html', form=dataset_form, name=name, title=TITLE)

    #except Exception as e:
    #    abort(500, description="Failed to mutate dataset.", original_exception=e)

        return page

@main_bp.route('/datasets')
def datasets(dataset_id=None):

    try:
        datasets = db_session.query(Dataset).all()
        page = render_template('dataset_table.html', datasets=datasets, title=TITLE)
        return page
    except Exception as e:
        abort(500, description="Failed to fetch datasets and render to table.", original_exception=e)



@main_bp.route('/about')
def about():
    return render_template('about.html', title=TITLE)

@main_bp.route('/instructions')
def instructions():
    return render_template('veluwe-metadata-portal-instructions.html', title=TITLE)

@main_bp.route('/contact')
def contact():
    return render_template('contact.html', title=TITLE)

@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template("errors/400.html", error=e), 400

@main_bp.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html", error=e), 500
