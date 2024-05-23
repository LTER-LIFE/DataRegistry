#!/usr/bin/python
# Title: routes.py
# Date start: 21/05/2024
# By: SanderV
# Use(s):
# Import(s):
from flask import Blueprint, render_template

# Define blueprint
homepage = Blueprint('homepage', __name__, template_folder='templates')

# Create the homepage route decorator
@homepage.route('/')
def home():
    return render_template('index.html')

@homepage.route('/search')
def search():
    return "<h1> Search page </h1>"
