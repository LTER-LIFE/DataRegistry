""" Models for the DCAT application.

The models are based on the DCAT specification:
https://www.w3.org/TR/vocab-dcat-3/

Initial Mandatory/Recommended/Optional properties are based on the DCAT-AP
specification: https://semiceu.github.io/DCAT-AP/releases/3.0.0/

For the help_text we are copying the description of the properties from
the DCAT-AP specification.

"""
import hashlib
import json

import shapely
from geoalchemy2 import Geometry
from shapely import GeometryCollection
from shapely.geometry import box
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float, Computed, or_, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.testing.schema import Table

from application.database import Base, db_session

metadata = Base.metadata


class Agent(Base):
    """Any entity carrying out actions with respect to the (Core) entities.

    Example: Publishers, Creators, etc.
    """

    __tablename__ = 'Agent'

    # Agent id
    agent_id = Column(Integer, primary_key=True, nullable=False)

    # Mandatory properties
    name = Column(String(255))

    # Recommended properties
    # A type of the agent that makes the Catalogue or Dataset available.
    type = Column(String(20), nullable=True)

    # Optional properties
    #         blank=True, null=True, help_text="An email address of the Agent."
    # Foaf:mbox
    mbox = Column(String(128), nullable=True)

    def to_jsonld(self):
        result = dict()
        result["foaf:name"] = self.name
        if self.type:
            result["@type"] = self.type
        return result

    def __str__(self):
        if self.name:
            return self.name
        if self.mbox:
            return self.mbox

    def web(self):
        return self.__str__()

    @classmethod
    def add_or_update_agent(cls, name="", organisation="", mbox="", persist=True):
        db_agent = db_session.query(Agent).filter(
                                                  or_(
                                                            and_(Agent.name == organisation, Agent.type == 'Organisation'),
                                                            and_(Agent.name == name,
                                                                 Agent.type == 'Person',
                                                                 Agent.mbox == mbox),
                                                            Agent.name == name
                                                         )
                                                    ).first()
        if not db_agent:
            db_agent = Agent()
            if mbox != "":
                db_agent.mbox = mbox
            if organisation != "":
                db_agent.name = organisation
                db_agent.type = 'Organisation'
            if name != "":
                db_agent.name = name
                db_agent.type = 'Person'
            if f"{mbox}{organisation}{name}" == "":
                return None
            if persist:
                db_session.add(db_agent)
                db_session.commit()
                db_session.flush()
        return db_agent


class Catalog(Base):
    """A catalogue that hosts the Datasets or Data Services being described.

     RDF Class:	dcat:Catalog
     Definition:	A curated collection of metadata about resources.
     Sub-class of:	dcat:Dataset
     Usage note:	A Web-based data catalog is typically represented as a single instance of this class.
     Usage note:	Datasets and data services are examples of resources in the context of a data catalog.
     See also:	6.5 Class: Catalog Record, 6.6 Class: Dataset

    """

    __tablename__ = 'Catalog'

    catalog_id = Column(Integer, primary_key=True, nullable=False)

    applicable_legislation = Column(String(255), nullable=True)
    # catalogue =
    contact_point = Column(String(255), nullable=True)

    title = Column(String(255), nullable=True)
    # A name given to the Catalogue.
    description = Column(Text, nullable=True)

    # A web page that acts as the main page for the Catalogue.
    homepage = Column(String(255), nullable=True)

    catalog_creator_id = Column(Integer, ForeignKey('Agent.agent_id'))
    creator = relationship("Agent", foreign_keys=[catalog_creator_id])

    datasets_in_catalogue = relationship("Dataset", foreign_keys='Dataset.dataset_catalog_id',
                                         back_populates="dataset_catalog", lazy=False)

    # A knowledge organization system used to classify the Catalogue's Datasets.
    themes = relationship('DataTheme', secondary='dataThemeCatalog')

    """
        on_delete=models.CASCADE,
        help_text="An entity (organisation) responsible for making the Catalogue available.",
    )
    """
    catalog_publisher_id = Column(Integer, ForeignKey('Agent.agent_id'))
    publisher = relationship("Agent", foreign_keys=[catalog_publisher_id])

    # Recommended properties
    """
    models.ForeignKey(
        "licenseDocument",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="A license under which the Catalogue can be used or reused.",
    )
    """
    catalog_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    license = relationship("LicenseDocument", foreign_keys=[catalog_license_id])

    # Helper table for many-to-many relation between datasets and keywords

    def to_jsonld(self):
        result = dict()
        result["@type"] = "dcat:Catalog"
        result["dct:title"] = self.title
        result["dct:description"] = self.description
        result["dct:publisher"] = self.publisher.to_jsonld()
        if self.homepage:
            result["foaf:homepage"] = {"@type": "foaf:Document", "foaf:Document": self.homepage}

        result["dcat:dataset"] = [dataset.to_jsonld() for dataset in self.dataset_set.all()]

        return result

    def __str__(self):
        return self.title


class Dataset(Base):
    """A conceptual entity that represents the information published."""

    __tablename__ = 'Dataset'

    """
    RDF Property: dcterms:identifier
    RANGE: Literal:Integer
    """
    dataset_id = Column(Integer, primary_key=True, nullable=False)
    # Mandatory properties

    ### LTER-LIFE subset
    """
    models.DateField(blank=True, null=True)
    
    This value will be automatically generated when the form is submitted.
    
    RDF Property:	dcterms:issued
    Definition:	Date of formal issuance (e.g., publication) of the resource.
    Range:	rdfs:Literal encoded using the relevant ISO 8601 Date and Time compliant string [DATETIME] and typed using 
    the appropriate XML Schema datatype [XMLSCHEMA11-2] (xsd:gYear, xsd:gYearMonth, xsd:date, or xsd:dateTime).
            Usage note:	This property SHOULD be set using the first known date of issuance.
    See also:	6.5.3 Property: listing date and 6.8.3 Property: release date
    """
    release_date = Column(DateTime, nullable=False)

    """
    RDF Property:	dcterms:language
        Definition:	A language of the resource. This refers to the natural language used for textual metadata (i.e., 
        titles, descriptions, etc.) of a cataloged resource (i.e., dataset or service) or the textual values of a 
        dataset distribution
    Range:	
        dcterms:LinguisticSystem
            Resources defined by the Library of Congress (ISO 639-1) should be used
              If a ISO 639-1 (two-letter) code is defined for language, then its corresponding IRI SHOULD be used
              
            Form will contain EN and NL
    """
    language = Column(String(255), nullable=False)

    """
    RDF Property: dcterms:creator
    Range: foaf:Agent
    """
    # TODO: create backreference in agent
    creator_id = Column(Integer, ForeignKey('Agent.agent_id'))
    creator = relationship("Agent", foreign_keys=[creator_id])

    """
   The name of the described dataset.
    Recommended spelling for this property is: (project attribute) subject (location attribute) (time attribute) (
    version). The parts in brackets are not mandatory, the others are. Abbreviations are only permitted in the title 
    if they are also written out, for example: “Large-scale Basic Map of the Netherlands (GBKN)”.

    This property can only be iterated to display the value in a different language. See multilingualism for dealing 
    with different languages.
    
    RDF property: 
       dcterms:title
    
    Range:
     rdfs:Literal

    """
    title = Column(String(255), nullable=False)

    """
    This property contains a description of the contents of the dataset. This is preferably at least three sentences 
    and a maximum of one paragraph long (2000 characters). The findability of the dataset is determined, among other 
    things, by the quality of the description. This includes different users, colleagues, but also others, 
    for whom the text must be understandable.

    This property can only be iterated to display the value in a different language. See multilingualism for dealing 
    with different languages.
    
    RDF property: 
       dcterms:description
    
    Range:
     rdfs:Literal
    """
    description = Column(Text)

    """
    RDF property: 
        dcterms:type
    Range:
        Literal
    
    """
    resource_type = Column(String(255), nullable=False)

    """   
    RDF property: dcat:contactPoint
    Range: foaf:Agent 
    TODO:not dcat standard which is vcard:Kind
    """
    dataset_contact_point_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_contact_point = relationship("Agent", foreign_keys=[dataset_contact_point_id])

    """
    RDF property: dcterms:publischer
    Range: foaf:Agent 
    TODO:not dcat standard which is vcard:Kind
    """
    dataset_publisher_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_publisher = relationship("Agent", foreign_keys=[dataset_publisher_id])


    """
    RDF property: dcterms:metadata_provider ??? TODO: makle sure this info is right 
    Range: foaf:Agent 
    TODO:not dcat standard which is vcard:Kind
    """
    dataset_metadata_provider_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_metadata_provider = relationship("Agent", foreign_keys=[dataset_metadata_provider_id])

    """
    RDF propery: dcat:keyword
    Range: rdf:Literal
    """

    dataset_keywords = relationship('Keyword', secondary='datasetKeyword')

    """
    RDF property: dcterms:temporal
    Range: dcterms:PeriodOfTime
    
    ISO 8601 start/end
    """
    temporal_coverage_start = Column(DateTime, nullable=False)
    temporal_coverage_end = Column(DateTime, nullable=False)

    """
    RDF property: dcat:temporalResolution
    Range: xsd:duration
    
    https://en.wikipedia.org/wiki/ISO_8601 tem
    "2007-03-01T13:00:00Z/2008-05-11T15:30:00Z"

    """
    temporal_resolution = Column(String(255), nullable=False)

    """
    RDF Propery: dcterms:spatial
    Range: dcterms:location
    
    ISO 19115 WKT!!! TODO: check 
    """
    dataset_spatial_covarage_id = Column(Integer, ForeignKey('Location.location_id'))
    dataset_spatial_covarage = relationship('Location', lazy=True)

    """
    RDF Properties: dcat:spatialResolutionInMeters
    Range: rdf:Literal
    """
    spatial_resolution = Column(String(255), nullable=False)

    """
    RDF Property: dcterms:license
    Range: dcterms:licenseDocument
    
    TODO: backreferecne
    """
    dataset_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    dataset_license = relationship("LicenseDocument", foreign_keys=[dataset_license_id])

    """
    RDF Property: dcterms:accessRights
    Range: dcterms:RightsStatement
    """
    access_rights = Column(String(255), nullable=False)

    ### Optional values

    """
    catalog = models.ForeignKey("Catalog", on_delete=models.CASCADE)
    """
    dataset_catalog_id = Column(Integer, ForeignKey('Catalog.catalog_id'))
    dataset_catalog = relationship("Catalog", foreign_keys=[dataset_catalog_id], back_populates="datasets_in_catalogue")

    # Recommended properties
    # TODO: description is mandatory

    """
        models.ManyToManyField(
        "DataTheme",
        blank=True,
        help_text="A category of the Dataset. A Dataset may be associated with multiple themes.",
    )
    """
    dataset_themes = relationship('DataTheme', secondary='datasetDataTheme')

    # Optional properties
    """
    models.DateField(
        blank=True,
        null=True,
        help_text="The most recent date on which the Dataset was changed or modified.",
    )
    """
    modified = Column(DateTime, nullable=False)


    """
    RDF property: eml:taxonomic_coverage ??? TODO: makle sure this info is right 
    """
    taxonomic_coverage = Column(String(255), nullable=True)

    """
    RDF Property: dcat:landingPage
    Range: foaf:Document
    
    we will just use address for now
    """
    landing_page = Column(String(255), nullable=True)

    def to_jsonld(self):
        result = dict()
        result["dct:title"] = self.title
        if self.description:
            result["dct:description"] = self.description
        result["dcat:distribution"] = [d.to_jsonld() for d in self.distribution_set.all()]

        return result

    def __str__(self):
        return self.title


class Distribution(Base):
    """A physical embodiment of the Dataset in a particular format.

    Example: A CSV file, an RDF file, etc.
    """

    __tablename__ = 'Distribution'

    distribution_id = Column(Integer, primary_key=True, nullable=False)

    # Mandatory properties
    """
    dataset = models.ForeignKey("Dataset", on_delete=models.CASCADE)
    """
    distribution_dataset_id = Column(Integer, ForeignKey('Dataset.dataset_id'))
    catalog = relationship("Dataset", foreign_keys=[distribution_dataset_id])

    title = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    external_download_url = Column(String(255), nullable=True)
    external_access_url = Column(String(255), nullable=True)

    distribution_mediatype_id = Column(Integer, ForeignKey('MediaType.mediatype_id'))
    format = relationship("MediaType", foreign_keys=[distribution_mediatype_id])

    distribution_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    license = relationship("LicenseDocument", foreign_keys=[distribution_license_id])

    distribution_checksum_id = Column(Integer, ForeignKey('Checksum.checksum_id'))
    checksum = relationship("Checksum", foreign_keys=[distribution_checksum_id])

    def to_jsonld(self):
        result = dict()
        result["@type"] = "dcat:Distribution"
        result["dcat:accessURL"] = self.access_url
        if self.title:
            result["dct:title"] = self.title
        if self.description:
            result["dct:description"] = self.description
        return result

    def __str__(self):
        return self.title


class DataService(Base):
    """Operations that provides access to datasets or data processing functions.

    Example: APIs, Web Services, SPARQL endpoints, etc.
    """

    __tablename__ = 'DataService'

    dataservice_id = Column(Integer, primary_key=True, nullable=False)
    # Mandatory properties

    # A name given to the DataService.
    title = Column(String(255), nullable=True)

    # The root location or primary endpoint of the service (an IRI).
    endpoint_url = Column(String(255), nullable=True)

    # Optional properties
    # A free-text account of the DataService.
    description = Column(Text, nullable=True)

    """
        catalog = models.ForeignKey("Catalog", on_delete=models.CASCADE)

    """
    dataservice_catalog_id = Column(Integer, ForeignKey('Catalog.catalog_id'))
    catalog = relationship("Catalog", foreign_keys=[dataservice_catalog_id])

    license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    license = relationship("LicenseDocument", foreign_keys=[license_id])

    format = relationship('MediaType', secondary='dataserviceMediaType')


class MediaType(Base):
    """A set of media types from the DCAT-AP vocabulary."""

    __tablename__ = 'MediaType'

    mediatype_id = Column(Integer, primary_key=True, nullable=False)

    extension = Column(String(10), nullable=True)
    code = Column(String(10), nullable=True, unique=True)
    media_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    def __str__(self):
        return self.extension


class LicenseDocument(Base):
    """A set of licenses from the DCAT-AP vocabulary."""

    __tablename__ = 'LicenseDocument'

    license_document_id = Column(Integer, primary_key=True, nullable=False)

    # Recommended properties
    @property
    def type(self):
        return self.url_general or self.label

    label = Column(String(255), nullable=True)
    code = Column(String(255), nullable=False)
    url_general = Column(String(255), nullable=True)
    url_document = Column(String(255), nullable=True)

    def __str__(self):
        return self.label


class DataTheme(Base):
    """Themes used for dataset classification.

    This is the mandatory controlled vocabulary for
    the themeTaxonomy field of Catalogue. (As defined
    by DCAT-AP).

    https://op.europa.eu/s/y52L
    """

    __tablename__ = 'DataTheme'

    data_theme_id = Column(Integer, primary_key=True, nullable=False)
    code = Column(String(255), nullable=False, unique=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    def __str__(self):
        return self.label


class Checksum(Base):
    """A value that allows the contents of a file to be authenticated."""

    __tablename__ = 'Checksum'

    checksum_id = Column(Integer, primary_key=True, nullable=False)
    checksum_value = Column(String(255), nullable=False)
    algorithm = Column(String(10), nullable=True)

    def __str__(self):
        return f"{self.checksum_value} ({self.algorithm})"


class Keyword(Base):
    """A keyword or tag describing the Dataset."""

    __tablename__ = 'Keyword'
    keyword_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(50), nullable=False)
    slug = Column(String(50), nullable=True)

    def __str__(self):
        return self.name

    @classmethod
    def add_or_update_keywords(cls, keyword_names=None, keyword_ids=None, persist=True):
        """
        Add or Update a user, Add a user to the database, if it does not yet exist.


        @param keyword_names:
        @param keyword_ids: TODO: does this need to stay?
        @param persist: default True, if persist false is selected, just the data model will be built, but nothing will
                    be saved in database
        @return:
        """
        db_keywords = []
        for keyword in keyword_names.split(","):
            keyword = keyword.lower().strip()
            db_keyword = db_session.query(Keyword).filter_by(name=keyword).first()
            if not db_keyword:
                db_keyword = Keyword(name=keyword)
                if persist:
                    db_session.add(db_keyword)
                    db_session.commit()
                    db_session.flush()
            db_keywords.append(db_keyword)
        return db_keywords


class Location(Base):
    """
    The location class, based on Range: dcterms:location
    contains spatial information,

    """
    __tablename__ = 'Location'
    location_id = Column(Integer, primary_key=True, nullable=False)
    bbox = Column(Geometry(geometry_type='GEOMETRY', srid=-1), nullable=True)
    centroid = Column(Geometry(geometry_type='POINT', srid=-1), nullable=True)

    geometry = Column(Geometry(geometry_type="GEOMETRYCOLLECTION", srid=-1), nullable=False)

    # datasets_at_location = relationship("Dataset", back_populates="dataset_spatial_coverage", lazy=False)
    @classmethod
    def add_or_update_location(cls, location_id=None, bbox=None, centroid=None, geometry=None, persist=True):
        db_location = db_session.query(Location).filter_by(geometry=geometry).first()
        if not db_location:
            db_location = Location()
            if geometry:
                geometry_shape = shapely.from_wkt(geometry)

                if shapely.get_type_id(geometry_shape) != 7:
                    geometry_shape = GeometryCollection(geometry_shape)

                db_location.geometry = shapely.to_wkt(geometry_shape)
                db_location.centroid = shapely.to_wkt(geometry_shape.centroid)
                db_location.bbox = shapely.to_wkt(box(*geometry_shape.bounds))
            if persist:
                db_session.add(db_location)
                db_session.commit()
                db_session.flush()
        return db_location

    def to_shape(self, field="geometry", to="wkt"):
        if field in self.__dict__.keys():
            wkb_value = str(self.__dict__.get(field, "POLYGON EMPTY"))
            if wkb_value == 'None':
                spatial_coverage_wkb = GeometryCollection()
            else:
                spatial_coverage_wkb = shapely.wkb.loads(wkb_value)
            if to == "wkt":
                return shapely.to_wkt(spatial_coverage_wkb)
            if to == "geojson":
                return shapely.to_geojson(spatial_coverage_wkb)


dataThemeCatalog = Table('dataThemeCatalog', Base.metadata,
                         Column('data_theme_id', Integer, ForeignKey('DataTheme.data_theme_id'), primary_key=True),
                         Column('catalog_id', Integer, ForeignKey('Catalog.catalog_id'), primary_key=True))

datasetDataTheme = Table('datasetDataTheme', Base.metadata,
                         Column('data_theme_id', Integer, ForeignKey('DataTheme.data_theme_id'), primary_key=True),
                         Column('dataset_id', Integer, ForeignKey('Dataset.dataset_id'), primary_key=True))

datasetKeyword = Table('datasetKeyword', Base.metadata,
                       Column('keyword_id', Integer, ForeignKey('Keyword.keyword_id'), primary_key=True),
                       Column('dataset_id', Integer, ForeignKey('Dataset.dataset_id'), primary_key=True))

dataserviceMediaType = Table('dataserviceMediaType', Base.metadata,
                             Column('mediatype_id', Integer, ForeignKey('MediaType.mediatype_id'), primary_key=True),
                             Column('dataservice_id', Integer, ForeignKey('DataService.dataservice_id'),
                                    primary_key=True))

# class CatalogRecord(models.Model):
#     """A description of a Dataset's entry in the Catalogue.

#     It exists for catalogs where a distinction is made between metadata about a dataset or
#     service and metadata about the entry in the catalog about the dataset or
#     service. For example, the publication date property of the dataset reflects
#     the date when the information was originally made available by the
#     publishing agency, while the publication date of the catalog record is
#     the date when the dataset was added to the catalog.
#     """
#     pass

# class DatasetInSeries(Dataset):
#    __tablename__ = 'DataSetInSeries'
#    """Capture the case when a Dataset is a member of a Dataset Series."""
#
#    dataset_in_series_id = Column(Integer, primary_key=True, nullable=False)


# class DatasetSeries(Base):
#    """Datasets that are published separately, but share some characteristics."""
#
#    __tablename__ = 'DataSetSeries'
#
#    pass
