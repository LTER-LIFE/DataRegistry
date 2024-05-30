from sqlalchemy.ext.hybrid import hybrid_property

from . import db, pwd_context
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
    # collection year start
    collect_year_start = db.Column(db.Date(), nullable=False)
    # collection year end
    collect_year_end = db.Column(db.Date(), nullable=False)
    # polygon of the study area
    polygon_location = db.Column(GEOALC_Geo("GEOMETRYCOLLECTION"),
                                 nullable=True)

    def __repr__(self):
        return f'Title {self.title}'

    def to_dict(self):
        """
        Create a dictionary representation of the object.
        :return: Returns a dictionary representation of the object.
        """
        return {
            "dataset_id": self.id,
            "title": self.title,
            "description": self.description,
            "email": self.email,
            "contact_person": self.contact_person,
            "data_location": self.data_location,
            "institute": self.institute,
            "keywords": ",".join(key_word for key_word in self.keywords),
            "collect_year_start": self.collect_year_start,
            "collect_year_end": self.collect_year_end,
            "polygon_location": self.polygon_location,
        }

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(300), nullable=False, unique=True)
    # hashing the password with gett and sett
    _password = db.Column("password", db.String(255), nullable=False)

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = pwd_context.hash(value)

