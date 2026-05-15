import csv
import hashlib
import io
import json
import logging
import zipfile
import requests
import traceback
from collections import defaultdict
import time

from flask import render_template, Blueprint, flash, request, abort, redirect, session, url_for, send_file, jsonify

from flask import current_app as app
import jwt
import shapely
from sqlalchemy import exc

from application import search_index
from application.authentication import get_userinfo, valid_token, in_editor_group
from application.database import db_session
from application.forms import DatasetForm, LlmForm
from application.forms import DatasetForm, DatasetStagingForm
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location
from application.services import LlmMetadataService
from application.models import AgentStaging, KeywordStaging, CatalogStaging, ChecksumStaging, DataServiceStaging, DatasetStaging, DataThemeStaging, DistributionStaging, \
    LicenseDocumentStaging, MediaTypeStaging, LocationStaging

# Blueprint Configuration
# Here the static folder and the templates folder are annotated
proxy_prefix = app.config.get("PROXY_PREFIX")
url_prefix = f"{proxy_prefix}/".replace("//", "/") if proxy_prefix else "/"

# Blueprint Configuration
main_bp = Blueprint("main_bp", __name__, template_folder="templates", static_folder="static", url_prefix=url_prefix)


@main_bp.route('/')
def home():
    """
    The home endpoint, it will show a map containing all datasets

    A python dictionary will be create containing the centroid, geometry and properties of all datasets
    it will be shown as a json in the flask template.

    :return: rendered flask template from templates/index.html
    """
    try:
        es_datasets = search_index.fetch_all()

        datasets_shapes = defaultdict(dict)
        for es_dataset in es_datasets.body["hits"]["hits"]:
            dataset_dict = {
                "centroid": es_dataset.get("_source", {}).get("dataset_spatial_coverage", {}).get("centroid", None),
                "geometry": es_dataset.get("_source", {}).get("dataset_spatial_coverage", {}).get("geometry", None),
                "properties": {"id": es_dataset.get("_source", {}).get("dataset_id", None),
                               "title": _json_safe_string(es_dataset.get("_source", {}).get("title", None)),
                               "description": _json_safe_string(es_dataset.get("_source", {}).get("description", None)),
                               "creator": Agent(**es_dataset.get("_source", {}).get("creator", None)).web(),
                               "temporal_coverage":
                                   f"{es_dataset.get("_source", {}).get("temporal_coverage_start", None)} / "
                                   f"{es_dataset.get("_source", {}).get("temporal_coverage_end", None)}",
                               "url": es_dataset.get("_source", {}).get("url")
                               }
            }

            datasets_shapes[es_dataset.get("_source").get("dataset_id")] = dataset_dict

        user_logged_in = is_logged_in()
        if user_logged_in:
            user_info = get_userinfo(session.get("access_token"))

        page = render_template('index.html', list_o_geo=datasets_shapes, title='Map', user=user_logged_in)
        return page
    except exc.PendingRollbackError as pre:
        db_session.rollback()
        logging.error(traceback.format_exc())
        abort(500, description="Database error rolled back last change, please refresh. (F5/Ctrl+r)",
              original_exception=pre)

    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to fetch datasets and render to map.", original_exception=e)


@main_bp.route('/datasets/edit/<dataset_id>', methods=['GET', 'POST'])
@main_bp.route('/datasets/delete/<dataset_id>', methods=['GET'])
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
        llm_form = LlmForm()
        dataset = None

        # Delete the dataset or edit
        if request.url_rule.rule.find("delete") > -1 or request.url_rule.rule.find("edit") > -1:
            dataset = Dataset.query.get(dataset_id)

            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            if not is_logged_in():
                flash(f"Please login to modify a dataset.", "error")
                return redirect(url_for("main_bp.login"))
            if not in_editor_group(session.get('access_token')):
                flash(f"Please ask for editor access to an admin.", "error")
                return redirect(url_for("main_bp.home"))
            if request.url_rule.rule.find("delete") > -1:
                db_session.delete(dataset)
                db_session.commit()
                db_session.flush()
                flash(f"Deleted dataset {dataset_id}", "success")
            elif request.url_rule.rule.find("edit") > -1 or request.url_rule.rule.find("copy") > -1:
                dataset_form.from_dataset(dataset)

        # If the form validates
        if dataset_form.validate_on_submit():
            if request.url_rule.rule.find("edit") > -1:
                dataset = dataset_form.to_dataset(dataset)
                dataset = dataset_form.to_dataset(dataset)
                # Commit study to the database
                db_session.commit()
                db_session.flush()
            else:
                dataset = dataset_form.to_dataset(dataset)
                # Add to the database
                db_session.add(dataset)
                # Commit study to the database
                db_session.commit()
                db_session.flush()
            # Feedback
            flash(f"Added dataset with title {dataset.title}.", "success")

        page = render_template('dataset_form.html', form=dataset_form, name=name, llm_form=llm_form, title='Register your dataset')
        return page
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to mutate dataset.", original_exception=e)

@main_bp.route('/stageddatasets/edit/<dataset_id>', methods=['GET', 'POST'])
@main_bp.route('/stageddatasets/delete/<dataset_id>', methods=['GET'])
@main_bp.route('/stage_dataset', methods=['GET', 'POST'])
def stage_dataset(dataset_id=None):
    """
    Renders a form to stage (create) or edit or delete a new dataset

    :param dataset_id: The param dataset id can be used to Edit or Delete datasets

    :return: rendered flask template from templates/add_dataset.html
    """
    #
    try:
        name = None
        dataset_form = DatasetStagingForm()
        llm_form = LlmForm()
        dataset = None

        # Delete the dataset or edit
        if request.url_rule.rule.find("delete") > -1 or request.url_rule.rule.find("edit") > -1:
            dataset = DatasetStaging.query.get(dataset_id)

            if not dataset:
                flash(f"{dataset_id} does not exist.", "error")
            if not is_logged_in():
                flash(f"Please login to modify a dataset.", "error")
                return redirect(url_for("main_bp.login"))
            if not in_editor_group(session.get('access_token')):
                flash(f"Please ask for editor access to an admin.", "error")
                return redirect(url_for("main_bp.home"))
            if request.url_rule.rule.find("delete") > -1:
                db_session.delete(dataset)
                db_session.commit()
                db_session.flush()
                flash(f"Deleted dataset {dataset_id}", "success")
            elif request.url_rule.rule.find("edit") > -1 or request.url_rule.rule.find("copy") > -1:
                dataset_form.from_dataset(dataset)

        # If the form validates
        if dataset_form.validate_on_submit():
            if request.url_rule.rule.find("edit") > -1:
                dataset = dataset_form.to_dataset(dataset)
                dataset = dataset_form.to_dataset(dataset)
                # Commit study to the database
                db_session.commit()
                db_session.flush()
            else:
                dataset = dataset_form.to_dataset(dataset)
                # Add to the database
                db_session.add(dataset)
                # Commit study to the database
                db_session.commit()
                db_session.flush()
            # Feedback
            flash(f"Staged dataset with title {dataset.title}.", "success")

        page = render_template('dataset_form.html', form=dataset_form, name=name, llm_form=llm_form,
                               title="Register your dataset")
        return page
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to mutate dataset.", original_exception=e)

@main_bp.route('/dataset/from-ai/submit', methods=['POST'])
async def dataset_from_ai_submit():
    """Submit a URL to the LLM service and return the job_id immediately."""
    llm_form = LlmForm()
    try:
        if llm_form.validate_on_submit():
            service = LlmMetadataService()
            job_id = await service.submit_job(llm_form.dataset_url.data)
            return jsonify({"job_id": job_id})
        return jsonify({"error": "Invalid form"}), 400
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@main_bp.route('/dataset/from-ai/poll/<job_id>', methods=['GET'])
async def dataset_from_ai_poll(job_id):
    """Check the current status of an LLM job. Returns status and result when done."""
    try:
        service = LlmMetadataService()
        status, data = await service.check_job(job_id)
        return jsonify({"status": status, "data": data})
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@main_bp.route('/dataset/from-ai', methods=['POST'])
async def dataset_from_ai():
    """
    Bootstrap a dataset form using AI-extracted metadata from a URL.

    Accepts either:
    - A job_id (from the JS polling flow) to fetch a completed job result, or
    - A direct URL submission (legacy path via llm_form).
    """
    llm_form = LlmForm()
    llm_metadata_service = LlmMetadataService()

    name = "LLM Prefilled dataset"
    try:
        job_id = request.form.get("job_id")
        if job_id:
            _, dataset_json = await llm_metadata_service.check_job(job_id)
        elif llm_form.validate_on_submit():
            dataset_json = await llm_metadata_service.get_metadata(llm_form.dataset_url.data)
        else:
            return redirect(url_for('main_bp.add_dataset'))

        dataset = llm_form.to_dataset(dataset_json)

        dataset_form = DatasetForm()
        dataset_form.from_dataset(dataset)

        page = render_template('dataset_form.html', form=dataset_form, llm_form=llm_form, name=name, title="Register your dataset")
        return page
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description=f"Failed to fetch dataset for {llm_form.dataset_url.data}.", original_exception=e)


@main_bp.route('/datasets')
def datasets():
    """
    Renders a form to show all datasets from the Elasticsearch index.

    :return: rendered flask template from templates/dataset_table.html
    """
    download_list = session.get('download_list', [])
    return render_template(
        'dataset_table.html',
        title='Datasets',
        download_list=download_list,
    )


@main_bp.route('/Dataset/<int:dataset_id>')
def datasets_detail(dataset_id):
    """
    Renders the dataset detail page.

    :param dataset_id: The id of a dataset

    :return: rendered flask template from templates/dataset_detail.html
    """
    try:
        dataset = db_session.get(Dataset, dataset_id)
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to fetch dataset.", original_exception=e)

    if not dataset:
        abort(404)

    download_list = session.get('download_list', [])
    return render_template(
        'dataset_detail.html',
        dataset=dataset.to_dict(),
        title=dataset.title,
        is_dataset_in_download_list=dataset.dataset_id in download_list
    )


@main_bp.route('/stageddatasets')
@main_bp.route('/StagedDataset/<dataset_id>')
def stageddatasets(dataset_id=None):
    """
    Renders a form to show all datasets in a table form. When a dataset_id is given only one dataset is shown

    :param dataset_id: The param dataset id can be used to Edit or Delete datasets

    :return: rendered flask template from templates/dataset_table.html
    """
    try:
        if dataset_id:
            datasets_table = [DatasetStaging.query.get(dataset_id)]
        else:
            datasets_table = db_session.query(DatasetStaging).all()
        page = render_template('dataset_table.html', datasets=datasets_table, title="Staged datasets")
        return page
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to fetch datasets and render to table.", original_exception=e)


@main_bp.route('/download-list')
def download_list():
    dataset_ids = session.get('download_list', [])
    download_list = [Dataset.query.get(dataset_id) for dataset_id in dataset_ids]
    return render_template('download-list.html', download_list=download_list, title='Your download list')


@main_bp.route('/download-list/add/<int:dataset_id>')
def add_to_download_list(dataset_id):
    if 'download_list' not in session:
        session['download_list'] = []
    if dataset_id not in session['download_list']:
        session['download_list'].append(dataset_id)
        session.modified = True
    return redirect(request.referrer)


@main_bp.route('/download-list/remove/<int:dataset_id>')
def remove_from_download_list(dataset_id):
    download_list = session.get('download_list', [])
    if dataset_id in download_list:
        download_list.remove(dataset_id)
        session['download_list'] = download_list
        session.modified = True
    return redirect(request.referrer)


@main_bp.route('/download-list/empty')
def empty_download_list():
    session.pop('download_list', None)
    return redirect(request.referrer)


@main_bp.route('/download-list/export')
def export_download_list():
    dataset_ids = session.get('download_list', [])
    if len(dataset_ids) > 0:
        stream = io.BytesIO()
        # Create Zip archive with one GeoJSON file per dataset, and a CSV file
        # as Table of Content (TOC)
        with zipfile.ZipFile(stream, 'w') as zf:
            toc_entries = []
            for dataset_id in dataset_ids:
                dataset = Dataset.query.get(dataset_id)
                dataset_geojson = _geojson_dump(dataset.to_dict())
                dataset_encoded = dataset_geojson.encode()
                dataset_hash = hashlib.md5(dataset_encoded).hexdigest()
                # Add JSON file to Zip archive
                with zf.open(f'{dataset_hash}.json', 'w') as f:
                    f.write(dataset_encoded)
                toc_entries.append({'hash': dataset_hash, 'title': dataset.title})
            # Add CSV file to Zip archive
            with zf.open("TOC.csv", "w") as csvf:
                # ZipFile expects binary, while the CSV writer gives strings
                with io.TextIOWrapper(csvf) as f:
                    writer = csv.DictWriter(f, fieldnames=toc_entries[0].keys())
                    writer.writeheader()
                    writer.writerows(toc_entries)
        stream.seek(0)
        return send_file(stream,
                         mimetype='application/zip',
                         as_attachment=True,
                         download_name='datasets.zip')


@main_bp.route('/rebuild')
def rebuild_index():
    """
    Fetch all datasets from database, Delete old index, Build new index from the fetched datasets.

    Renders a page the number of datasets in both the database and the index, the index shouldn't be too far behind
    and the time the operations took.

    :return: rendered flask template from templates/dashboard.html
    """
    # get all datasets from database
    start = time.time()

    db_datasets = db_session.query(Dataset).all()
    db_duration = '{:f}'.format(time.time() - start)

    database_datasets_stats =  {"total": len(db_datasets),
                             "duration": f"Fetched all full datasets in {db_duration}"}

    start = time.time()
    indexed_datasets = search_index.rebuild_index(db_datasets)

    idx_duration = '{:f}'.format(time.time() - start)
    index_datasets_stats =  {"total": len(indexed_datasets),
                             "duration": f"Indexing took {idx_duration}"}

    return render_template('dashboard.html',
                           database_datasets_stats=database_datasets_stats,
                           index_datasets_stats=index_datasets_stats)

@main_bp.route('/query', methods=['POST'])
def query_index():
    """
    Renders a form to show all datasets in a table form. When a dataset_id is given only one dataset is shown

    :param dataset_id: The param dataset id can be used to Edit or Delete datasets

    :return: rendered flask template from templates/dataset_table.html
    """
    try:
        query_obj = request.get_json()


        if not query_obj == {}:
            query = search_index.build_es_query(query_obj)
            es_datasets = search_index.query(query)
        else:
            es_datasets = search_index.fetch_all()


        for hit in es_datasets.raw["hits"]["hits"]:
            source = {}
            for key, value in hit.get("_source").items():
                if isinstance(value, dict):
                    if value.get("agent_id", None):
                        source[key] = Agent(agent_id=value.get("agent_id"), name=value.get("name"),
                                            type=value.get("type"), mbox=value.get("mbox")).web()
                    elif value.get("keyword_id", None):
                        source[key] = value
                    elif value.get("license_document_id", None):
                        source[key] = value["code"]
                    else:
                        source[key] = value
                else:
                    source[key] = value
            hit["_source"] = source


        return jsonify(es_datasets.raw["hits"])
    except Exception as e:
        logging.error(traceback.format_exc())
        abort(500, description="Failed to query .", original_exception=e)


@main_bp.route('/dashboard')
def dashboard():
    """
    Renders a page the number of datasets in bot the database and the index, the index shouldn't be too far behind

    :return: rendered flask template from templates/dashboard.html
    """
    start = time.time()

    db_datasets_count = db_session.query(Dataset.dataset_id).count()
    db_duration = '{:f}'.format(time.time() - start)

    database_datasets_stats =  {"total": db_datasets_count,
                             "duration": db_duration}

    index_datasets = search_index.fetch_all()
    index_datasets_stats =  {"total": len(index_datasets.body["hits"]["total"]),
                             "duration": index_datasets.meta.duration}

    return render_template('dashboard.html',
                           database_datasets_stats=database_datasets_stats,
                           index_datasets_stats=index_datasets_stats,
                           title='Dashboard')

@main_bp.context_processor
def download_list_item_count():
    """
    Make the size of the download list globally available.

    This is to update the header that displays the number of items in the download list.

    :return: Number of elements in the download list
    :rtype: dict
    """
    download_list = session.get("download_list", [])
    return dict(download_list_item_count=len(download_list))


@main_bp.route('/login')
def login():
    """
    Redirect to surfconnext for login information

    :return: Redirect to an url that is formed from the surf authorization endpoint, Scopes, SURF_CLIENT_ID,
    redirect_uri, code challenge, code challenge method
    """
    return redirect(requests.get(url=app.config['SURF_DOTWELLKNOWN_CONFIG']['authorization_endpoint'],
                                 params={"response_type": "code", "client_id": app.config['SURF_CLIENT_ID'],
                                         "scope": "openid aarc eduperson_entitlement "
                                                  "eduperson_orcid "
                                                  "eduperson_principal_name eduperson_scoped_affiliation email"
                                                  "entitlements orcid profile uid "
                                                  "voperson_external_affiliation voperson_external_id voperson_id",
                                         "redirect_uri": app.config['SURF_REDIRECT_URI'],
                                         "code_challenge": app.config['CODE_CHALLENGE'],
                                         "code_challenge_method": "S256"}, allow_redirects=False).url)


@main_bp.route('/authorized/')
def authorized():
    """
    Handle OAuth2 callback by exchanging authorization code for access token.

    Retrieves the authorization code from the request, exchanges it for an access token,
    stores the token in the session, and redirects the user to the home page.

    :return: A redirect response to the home page, or an error message if the token exchange fails.
    :rtype: flask.Response or str
    """
    code = request.args.get('code')

    token_params = {'grant_type': 'authorization_code', 'code': code, 'client_id': app.config['SURF_CLIENT_ID'],
                    'client_secret': app.config['SURF_CLIENT_SECRET'], 'redirect_uri': app.config['SURF_REDIRECT_URI'],
                    'code_verifier': app.config['CODE_VERIFIER'], }

    access_token = requests.post(app.config['SURF_DOTWELLKNOWN_CONFIG']['token_endpoint'], data=token_params).json()

    if access_token is None:
        logging.error("Error while getting access token")
        return "Error while getting access token"
    session['access_token'] = access_token
    return redirect(url_for("main_bp.home"))


@main_bp.route('/about')
def about():
    """
    Renders a simple about page.

    :return: rendered flask template from templates/about.html    """
    return render_template('about.html', title='About the LTER-NL Data Registry')


@main_bp.route('/instructions')
def instructions():
    """
    Renders a simple instructions page.

    :return: rendered flask template from templates/instructions.html
    """
    return render_template('instructions.html')


@main_bp.route('/contact')
def contact():
    """
    Redirects to about page.

    :return: A redirect response to the about page
    """
    return redirect(url_for("main_bp.about"))


@main_bp.errorhandler(404)
def page_not_found(e):
    """
    Prints a 404 error message

    :param e: The exception is printed on the page
    :return: rendered flask template from templates/errors/400.html
    """
    return render_template("errors/400.html", error=e, title="Page not found"), 404


@main_bp.errorhandler(500)
def internal_server_error(e):
    """
    Prints a 500 error message

    :param e: The exception is printed on the page
    :return: rendered flask template from templates/errors/500.html
    """
    return render_template("errors/500.html", error=e, title="Internal server error"), 500


def is_logged_in():
    """
    Check if the user is logged in correctly
    :return:
    """
    if not session.get("access_token", None):
        logging.info("Not logged in")
        return False
    else:
        if session["access_token"].get("error", None):
            logging.error(session["access_token"])
            return False

        token_extract = jwt.decode(session["access_token"]["access_token"], algorithms=["ES256"],
                                   options={"verify_signature": False})

        return valid_token(token_extract)


def _json_safe_string(string):
    """
    Some fields can contain breaking code for json, this function can be used to clean this fields
    """
    return string.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _geojson_dump(dataset):
    """
    Encode dataset into GeoJSON, sorting keys
    """
    dataset_ = dataset.copy()
    dataset_spatial_coverage = dataset_.pop('dataset_spatial_coverage', {})
    geometry = dataset_spatial_coverage.pop('geometry', {})
    geometry = _drop_geometry_collection(geometry)
    properties = {**dataset_, **dataset_spatial_coverage}
    return json.dumps(dict(type="Feature",
                           geometry=geometry,
                           properties=properties),
                      sort_keys=True)


def _drop_geometry_collection(geometry):
    """
    Drop the geometry collection for collections with a single element
    """
    if geometry:
        geom = shapely.from_geojson(json.dumps(geometry))
        # if we have a geometry collection (.is_simple is False) and the number
        # of elements is equal to one, extract the geometry entry and map it to
        # GeoJSON
        if (not geom.is_simple) and (len(geom.geoms) == 1):
            geom = geom.geoms[0]
            geometry = json.loads(shapely.to_geojson(geom))
    return geometry
