import json
import logging
from collections import defaultdict
from datetime import datetime

import requests
from flask import render_template, Blueprint, flash, request, abort, redirect, session, url_for
from flask import current_app as app
import jwt

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
def home():
    """
    The home endpoint, it will show a map containing all datasets

    A python dictionary will be create containing the centroid, geometry and properties of all datasets
    it will be shown as a json in the flask template.

    :return: rendered flask template from templates/index.html
    """
    try:
        all_datasets = db_session.query(Dataset).all()

        datasets_shapes = defaultdict(dict)
        for dataset in all_datasets:
            dataset_dict = {
                "centroid": json.loads(dataset.dataset_spatial_covarage.to_shape(field="centroid", to="geojson")),
                "geometry": json.loads(dataset.dataset_spatial_covarage.to_shape(field="geometry", to="geojson")),
                "properties": {"id": dataset.title, "user_logged_intitle": dataset.title,
                               "description": dataset.description, "creator": str(dataset.creator),
                               "temporal_coverage": f"{dataset.temporal_coverage_start} / "
                                                    f"{dataset.temporal_coverage_end}"}}

            datasets_shapes[dataset.dataset_id] = dataset_dict
        user_logged_in = is_logged_in()

        page = render_template('index.html', list_o_geo=datasets_shapes, title=TITLE, user=user_logged_in)
        return page
    except Exception as e:
        abort(500, description="Failed to fetch datasets and render to map.", original_exception=e)


@main_bp.route('/datasets/edit/<dataset_id>')
@main_bp.route('/datasets/delete/<dataset_id>')
@main_bp.route('/add_dataset', methods=['GET', 'POST'])
def add_dataset(dataset_id=None):
    """
    Renders a form to Edit or Create a new dataset

    :param dataset_id: The param dataset id can be used to Edit or Delete datasets

    :return: rendered flask template from templates/add_dataset.html
    """
    #
    try:
        name = None
        dataset_form = DatasetForm()
        # Validate the add study form
        if request.url_rule.rule.find("edit") > -1:
            dataset = Dataset.query.get(dataset_id)
            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            else:
                dataset_form.from_dataset(dataset)

        # Delete the dataset
        if request.url_rule.rule.find("delete") > -1 or request.url_rule.rule.find("edit") > -1:
            dataset = Dataset.query.get(dataset_id)
            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            if not is_logged_in():
                flash(f"Please login to modify a dataset.", "error")
                return redirect(url_for("main_bp.login"))
            if request.url_rule.rule.find("delete") > -1:
                db_session.delete(dataset)
                db_session.commit()
                db_session.flush()
                flash(f"Deleted dataset {dataset_id}", "success")

        # Copy the dataset (not implemented yet)
        if request.url_rule.rule.find("copy") > -1:
            pass

        # If the form validates
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
        return page
    except Exception as e:
        abort(500, description="Failed to mutate dataset.", original_exception=e)


@main_bp.route('/datasets')
@main_bp.route('/Dataset/<dataset_id>')
def datasets(dataset_id=None):
    """
    Renders a form to show all datasets in a table form. When a dataset_id is given only one dataset is shown

    :param dataset_id: The param dataset id can be used to Edit or Delete datasets

    :return: rendered flask template from templates/dataset_table.html
    """
    try:
        if dataset_id:
            datasets_table = [Dataset.query.get(dataset_id)]
        else:
            datasets_table = db_session.query(Dataset).all()
        page = render_template('dataset_table.html', datasets=datasets_table, title=TITLE)
        return page
    except Exception as e:
        abort(500, description="Failed to fetch datasets and render to table.", original_exception=e)


@main_bp.route('/login')
def login():
    """

    :return:
    """
    return redirect(requests.get(url=app.config['SURF_DOTWELLKNOWN_CONFIG']['authorization_endpoint'],
                                 params={"response_type": "code", "client_id": app.config['SURF_CLIENT_ID'],
                                         "scope": "openid profile email",
                                         "redirect_uri": app.config['SURF_REDIRECT_URI'],
                                         "code_challenge": app.config['CODE_CHALLENGE'],
                                         "code_challenge_method": "S256"}, allow_redirects=False).url)


@main_bp.route('/authorized/')
def authorized():
    code = request.args.get('code')

    token_params = {'grant_type': 'authorization_code', 'code': code, 'client_id': app.config['SURF_CLIENT_ID'],
                    'client_secret': app.config['SURF_CLIENT_SECRET'], 'redirect_uri': app.config['SURF_REDIRECT_URI'],
                    'code_verifier': app.config['CODE_VERIFIER'], }

    access_token = requests.post(app.config['SURF_DOTWELLKNOWN_CONFIG']['token_endpoint'], data=token_params).json()

    if access_token is None:
        return "Error while getting access token"
    session['access_token'] = access_token
    return redirect('/')


@main_bp.route('/about')
def about():
    """
    Renders a simple about page.

    :return: rendered flask template from templates/about.html    """
    return render_template('about.html', title=TITLE)


@main_bp.route('/instructions')
def instructions():
    """
    Renders a simple instructions page.

    :return: rendered flask template from templates/veluwe-metadata-portal-instructions.html
    """
    return render_template('veluwe-metadata-portal-instructions.html', title=TITLE)


@main_bp.route('/contact')
def contact():
    """
    Renders a simple contact page.

    :return: rendered flask template from templates/contact.html
    """
    return render_template('contact.html', title=TITLE)


@main_bp.errorhandler(404)
def page_not_found(e):
    """
    Prints a 404 error message

    :param e: The exception is printed on the page
    :return: rendered flask template from templates/errors/400.html
    """
    return render_template("errors/400.html", error=e), 400


@main_bp.errorhandler(500)
def internal_server_error(e):
    """
    Prints a 500 error message

    :param e: The exception is printed on the page
    :return: rendered flask template from templates/errors/500.html
    """
    return render_template("errors/500.html", error=e), 500


def valid_token(token):
    """
    @param: token is a dictionary containing msal token
    @return: Boolean for the validity of the token

    according to M$ @ https://learn.microsoft.com/en-us/azure/active-directory/develop/id-tokens

     - Timestamps: the iat, nbf, and exp timestamps should all fall before or after the current time, as appropriate.
     - Audience: the aud claim should match the app ID for your application.
     - Nonce: the nonce claim in the payload must match the nonce parameter passed into the /authorize endpoint during
       the initial request.

    """
    try:
        if not token:
            return False
        if token.get("error"):
            logging.warning(f"login failed: {token.get('error_description')}")
            return False
        if datetime.fromtimestamp(token.get("exp")) < datetime.now():
            return False
        if datetime.fromtimestamp(token.get("iat")) > datetime.now():
            return False
        if token.get("client_id") != app.config.get("SURF_CLIENT_ID"):
            return False
    except Exception as e:
        logging.warning(f"login failed: {token} with {e}")
        return False

    return True


def is_logged_in():
    """
    Check if the user is logged in correctly
    :return:
    """
    if not session.get("access_token", None):
        return False
    else:
        token_extract = jwt.decode(session["access_token"]["access_token"], algorithms=["ES256"],
                                   options={"verify_signature": False})
        return valid_token(token_extract)
