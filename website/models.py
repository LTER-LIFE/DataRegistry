from . import db
from geoalchemy2 import Geometry as GEOALC_Geo
from shapely import geometry as SHAPE_Geo
import os
import datetime

class Catalog(db.Model):
    __tablename__ = "CatalogMeta"
    id = db.Column(db.Integer, primary_key=True)
    # title of a dataset
    title = db.Column(db.String(200), nullable=False)
    # describe the dataset
    description = db.Column(db.String(500), nullable=False)
    # email
    email = db.Column(db.String(300), nullable=False)
    # contact person
    contact_person = db.Column(db.String(300), nullable=False)
    # data location hyperlink
    data_location = db.Column(db.String())
    # later change to foreignkey institute
    institute = db.Column(db.String(500))
    # keywords
    keywords = db.Column(db.String(500), nullable=False)
    # collection year
    collect_year = db.Column(db.Integer, nullable=False)
    # polygon of the study area
    polygon_location = db.Column(GEOALC_Geo("GEOMETRYCOLLECTION"), nullable=True)

    def __repr__(self):
        return f'Title {self.title}'

