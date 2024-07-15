# Catalog model


from sqlalchemy.ext.hybrid import hybrid_property
from extensions import db
import geoalchemy2


class Catalog(db.Model):
    __tablename__ = "CatalogMeta"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    keywords = db.Column(db.String(500), nullable=True)
    # collection year start
    collect_year_start = db.Column(db.Date(), nullable=False)
    # collection year end
    collect_year_end = db.Column(db.Date(), nullable=False)
    # collection_interval
    collect_interval = db.Column(db.String(), nullable=True)
    # Eco-sphere (as per LTER-LIFE)
    ecosphere_type = db.Column(db.String(), nullable=True)

    # polygon of the study area
    polygon_location = db.Column(geoalchemy2.Geometry("GEOMETRYCOLLECTION", -1),
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
            "keywords": self.keywords,
            "collect_year_start": self.collect_year_start,
            "collect_year_end": self.collect_year_end,
            "polygon_location": self.polygon_location
        }
