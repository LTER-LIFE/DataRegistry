import folium
from folium.plugins import MarkerCluster, MousePosition
from flask import Blueprint, jsonify, render_template, request
from flask_restful import Api
from marshmallow import ValidationError
from website.resources.user import UserList, UserResource

# Set up the blueprints
homepage = Blueprint('homepage', __name__, url_prefix='/',
                      template_folder='templates')
app = Api(homepage)

app.add_resource(UserList, '/users')
app.add_resource(UserResource, '/users/<int:id>')

@homepage.errorhandler(ValidationError)
def validation_error(e):
    return jsonify(e.messages), 400


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


@homepage.route('/search')
def search():
    return "<h1>Search</h1>"


@homepage.route('/contact')
def contact():
    return "<h1>Contact</h1>"


@homepage.route('/about')
def about():
    return "<h1>About</h1>"


@homepage.route('/Sign In')
def sign_in():
    return "<h1>Sign In</h1>"

