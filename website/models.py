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
    contact = db.Column(db.String(300), nullable=False)
    # data location
    data_location = db.Column(db.String())
    # later change to foreignkey institute
    institute = db.Column(db.String(500))
    # tags/keywords
    keywords = db.Column(db.String())
    # date/time of collection of data
    # date_collection = db.Column(db.Datetime(), nullable=True)
    # location flag
    flag_location = db.Column(GEOALC_Geo("POINT"),
                              nullable=False)
    # polygon
    polygon_location = db.Column(GEOALC_Geo("GEOMETRYCOLLECTION"), nullable=True)

    def __repr__(self):
        return f'Title {self.title}'


