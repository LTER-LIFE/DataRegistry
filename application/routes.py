import json

from flask import render_template, Blueprint, flash
from flask import current_app as app
from application.database import db_session
from application.forms import DatasetForm
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType

# Blueprint Configuration
# Here the static folder and the templates folder are annotated
proxy_prefix = app.config.get("PROXY_PREFIX")
url_prefix = f"{proxy_prefix}/".replace("//", "/") if proxy_prefix else "/"

# Blueprint Configuration
main_bp = Blueprint("main_bp", __name__, template_folder="templates", static_folder="static", url_prefix=url_prefix)

@main_bp.route('/')
def home(dataset_id=None):
    data_json = json.loads("""{ "type": "FeatureCollection",
  "features": [
    { "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [102.0, 0.5]},
      "properties": {"prop0": "value0"}
      },
    { "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
          ]
        },
      "properties": {
        "prop0": "value0",
        "prop1": 0.0
        }
      },
    { "type": "Feature",
       "geometry": {
         "type": "Polygon",
         "coordinates": [
           [ [100.0, 0.0], [101.0, 0.0], [101.0, 1.0],
             [100.0, 1.0], [100.0, 0.0] ]
           ]

       },
       "properties": {
         "prop0": "value0",
         "prop1": {"this": "that"}
         }
       }
    ]
  }
    """)

    return render_template('index.html', list_o_geo=json.dumps(data_json))

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
        # Feedback
        flash(("Entry '{}' is now being reviewed!").format(dataset.title))

    return render_template('dataset_form.html', form=dataset_form, name=name)
