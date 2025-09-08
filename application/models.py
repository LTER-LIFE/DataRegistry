""" Models for the DCAT application.

The models are based on the DCAT specification:
https://www.w3.org/TR/vocab-dcat-3/

Initial Mandatory/Recommended/Optional properties are based on the DCAT-AP
specification: https://semiceu.github.io/DCAT-AP/releases/3.0.0/

For the help_text we are copying the description of the properties from
the DCAT-AP specification.

"""
import os.path
import shutil
import tempfile
import zipfile

import geopandas as gpd
import shapely
from geoalchemy2 import Geometry
from rdflib import Namespace, Graph, Literal, FOAF, RDF, DCTERMS, DCAT
from shapely import GeometryCollection
from shapely.geometry import box, shape
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, or_, and_
from sqlalchemy.orm import relationship
from sqlalchemy.testing.schema import Table

from application.database import Base, db_session

DCATAP_NS = Namespace("http://data.europa.eu/r5r/")
SCHEMA_ORG_NS = Namespace("https://schema.org/")
EML_COV_NS = Namespace("https://eml.ecoinformatics.org/coverage-2.2.0/")
SPDX = Namespace("http://spdx.org/rdf/terms#")

VS_PREFIX = "https://lter-life-experience.org/veluwesearch"
VSA = Namespace(f"{VS_PREFIX}/Agent/")
VSC = Namespace(f"{VS_PREFIX}/Catalog/")
VSDS = Namespace(f"{VS_PREFIX}/Dataset/")
VSDT = Namespace(f"{VS_PREFIX}/DataTheme/")
VSLD = Namespace(f"{VS_PREFIX}/LicenseDocument/")
VSL = Namespace(f"{VS_PREFIX}/Location/")
VSD = Namespace(f"{VS_PREFIX}/Distribution/")
VSMT = Namespace(f"{VS_PREFIX}/MediaType/")

metadata = Base.metadata

GRAPH_PERSIST_HELP_TEXT = """
            .. csv-table::
               :header: "RDF Format", "Keyword", "Notes"

               "Turtle",    "turtle, ttl or turtle2",     "turtle2 is just turtle with more spacing & linebreaks"
               "RDF/XML",   "xml or pretty-xml",     "Was the default format, rdflib < 6.0.0"
               "JSON-LD",   "json-ld",     "There are further options for compact syntax and other JSON-LD variants"
               "N-Triples", "ntriples, nt or nt11",     "nt11 is exactly like nt, only utf8 encoded"
               "Notation-3","n3",     "N3 is a superset of Turtle that also caters for rules and a few other things"

               "Trig",     "trig",     "Turtle-like format for RDF triples + context (RDF quads) and thus multiple
               graphs"
               "Trix",     "trix",     "RDF/XML-like format for RDF quads"
               "N-Quads",   "nquads",     "N-Triples-like format for RDF quads"
"""


class Agent(Base):
    """Any entity carrying out actions with respect to the (Core) entities.

    Example: Publishers, Creators, etc.
    """

    __tablename__ = 'Agent'

    agent_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255))
    type = Column(String(20), nullable=True)
    mbox = Column(String(128), nullable=True)

    def to_graph(self):
        """

        @return: Agent object in RDFlib graph format
        """
        g = Graph()
        # Add namespaces to the graph
        g.bind("foaf", FOAF)
        g.bind("vp_agent", VSA)

        # Create a foaf:Agent instance
        agent = VSA[str(self.agent_id)]

        # Add properties to the agent
        g.add((agent, RDF.type, FOAF.Agent))
        g.add((agent, FOAF.name, Literal(self.name)))
        if self.type:
            g.add((agent, DCTERMS.type, Literal(self.type)))
        if self.type:
            g.add((agent, DCAT.mbox, Literal(self.mbox)))
        return g

    def rdf_serialize(self, out_format="json-ld"):
        f"""
        Runs the serialize function of RDFlib

        :param out_format: default output is json-ld other possibilities are: {GRAPH_PERSIST_HELP_TEXT}

        :return: the searialized graph in the format passed in out_fomat
        """
        return self.to_graph().serialize(format=out_format)

    def __str__(self):
        return self.web()

    def web(self):
        """
        A standard view to always view as much as possible for organizations and persons

        @return: string containing Name,type and/or mbox
        """
        if self.name and self.mbox:
            return f"<a href='mailto:{self.mbox}'>{self.name}</a>"
        if self.name:
            return self.name
        if self.mbox:
            return self.mbox

    @classmethod
    def add_or_update_agent(cls, name="", organisation="", mbox="", persist=True):
        """
        Add or update an agent to the database, using a name, organization, mailbox

        An Agent can be a Person or an Organization

        :param name: name of person
        :param organisation: Name of organization
        :param mbox: usually an email address
        :param persist: True to persist in the database False to just create the objects
        :return: An Agent Object
        """
        db_agent = db_session.query(Agent).filter(
            or_(and_(Agent.name == organisation, Agent.type == 'Organisation', Agent.mbox == mbox),
                and_(Agent.name == name, Agent.type == 'Person', Agent.mbox == mbox))).first()
        if not db_agent:
            db_agent = Agent()
            if mbox != "":
                db_agent.mbox = mbox
            else:
                db_agent.mbox = None
            if organisation != "":
                db_agent.name = organisation
                db_agent.type = 'Organisation'
            else:
                db_agent.type = 'Person'
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
    contact_point = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    homepage = Column(String(255), nullable=True)

    # Relations

    catalog_creator_id = Column(Integer, ForeignKey('Agent.agent_id'))
    creator = relationship("Agent", foreign_keys=[catalog_creator_id])
    datasets_in_catalogue = relationship("Dataset", foreign_keys='Dataset.dataset_catalog_id',
                                         back_populates="dataset_catalog", lazy=False)

    themes = relationship('DataTheme', secondary='dataThemeCatalog')

    catalog_publisher_id = Column(Integer, ForeignKey('Agent.agent_id'))
    publisher = relationship("Agent", foreign_keys=[catalog_publisher_id])

    catalog_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    license = relationship("LicenseDocument", foreign_keys=[catalog_license_id])

    # Helper table for many-to-many relation between datasets and keywords

    def to_graph(self):
        """

        @return: Agent object in RDFlib graph format
        """

        g = Graph()
        # Add namespaces to the graph
        g.bind("dcatap", DCATAP_NS)
        g.bind("vs_agent", VSA)
        g.bind("vs_catalog", VSC)

        catalog = VSC[str(self.catalog_id)]

        # Add properties to the agent
        g.add((catalog, RDF.type, DCAT.Catalog))
        if self.applicable_legislation:
            g.add((catalog, DCATAP_NS.applicableLegislation, Literal(self.name)))
        if self.contact_point:
            g.add((catalog, DCAT.contactPoint, Literal(self.contact_point)))
        if self.title:
            g.add((catalog, DCTERMS.title, Literal(self.title)))
        if self.description:
            g.add((catalog, DCTERMS.description, Literal(self.description)))
        if self.homepage:
            g.add((catalog, FOAF.homepage, Literal(self.description)))
        if self.creator:
            g.add((catalog, DCTERMS.creator, self.creator.to_graph()))
        if self.publisher:
            g.add((catalog, DCTERMS.publisher, self.publisher.to_graph()))
        if self.license:
            g.add((catalog, DCTERMS.license, self.license.to_graph()))
        for dataset in self.datasets_in_catalogue:
            g.add((catalog, DCAT.dataset, dataset.to_graph()))
        for theme in self.themes:
            g.add((catalog, DCAT.themeTaxonomy, theme.to_graph()))
        return g

    def rdf_serialize(self, out_format="json-ld"):
        f"""
        Runs the serialize function of RDFlib

        @param out_format: default output is json-ld other possibilities are: {GRAPH_PERSIST_HELP_TEXT}

        @return:
        """
        return self.to_graph().serialize(format=out_format)

    def __str__(self):
        return self.title


class Dataset(Base):
    """A conceptual entity that represents the information published."""

    __tablename__ = 'Dataset'

    dataset_id = Column(Integer, primary_key=True, nullable=False)
    release_date = Column(DateTime, nullable=False)
    language = Column(String(255), nullable=False)

    creator_id = Column(Integer, ForeignKey('Agent.agent_id'))
    creator = relationship("Agent", foreign_keys=[creator_id])
    title = Column(String(255), nullable=False)
    description = Column(Text)
    resource_type = Column(String(255), nullable=False)

    dataset_contact_point_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_contact_point = relationship("Agent", foreign_keys=[dataset_contact_point_id])

    dataset_publisher_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_publisher = relationship("Agent", foreign_keys=[dataset_publisher_id])

    dataset_metadata_provider_id = Column(Integer, ForeignKey('Agent.agent_id'))
    dataset_metadata_provider = relationship("Agent", foreign_keys=[dataset_metadata_provider_id])

    dataset_keywords = relationship('Keyword', secondary='datasetKeyword')

    temporal_coverage_start = Column(DateTime, nullable=False)
    temporal_coverage_end = Column(DateTime, nullable=True)

    temporal_resolution = Column(String(255), nullable=False)

    dataset_spatial_coverage_id = Column(Integer, ForeignKey('Location.location_id'))
    dataset_spatial_coverage = relationship('Location', lazy=True)

    spatial_resolution = Column(String(255), nullable=False)

    dataset_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    dataset_license = relationship("LicenseDocument", foreign_keys=[dataset_license_id])

    access_rights = Column(String(255), nullable=False)

    dataset_catalog_id = Column(Integer, ForeignKey('Catalog.catalog_id'))
    dataset_catalog = relationship("Catalog", foreign_keys=[dataset_catalog_id], back_populates="datasets_in_catalogue")

    dataset_themes = relationship('DataTheme', secondary='datasetDataTheme')

    modified = Column(DateTime, nullable=False)
    taxonomic_coverage = Column(String(255), nullable=True)
    landing_page = Column(String(255), nullable=True)
    public_id = Column(String(255), nullable=True)

    def to_graph(self):
        """

        @return: Agent object in RDFlib graph format
        """
        g = Graph()
        # Add namespaces to the graph
        g.bind("foaf", FOAF)
        g.bind("dcat", DCAT)
        g.bind("eml_cov", EML_COV_NS)
        g.bind("dcterms", DCTERMS)
        g.bind("vp_agent", VSA)
        g.bind("vp_catalog", VSC)
        g.bind("vp_license", VSLD)
        g.bind("vp_dataset", VSDS)
        g.bind("vp_data_theme", VSDT)

        # Create a dcat:Dataset instance
        dataset = VSDS[str(self.dataset_id)]

        # Add properties to the agent
        g.add((dataset, RDF.type, DCAT.Dataset))

        if self.release_date:
            g.add((dataset, DCTERMS.issued, Literal(self.release_date)))
        if self.language:
            g.add((dataset, DCTERMS.language, Literal(self.language)))
        if self.creator:
            g.add((dataset, DCTERMS.creator, VSA[str(self.creator.agent_id)]))
        if self.title:
            g.add((dataset, DCTERMS.title, Literal(self.title)))
        if self.description:
            g.add((dataset, DCTERMS.description, Literal(self.description)))
        if self.resource_type:
            g.add((dataset, DCTERMS.type, Literal(self.resource_type)))
        if self.dataset_contact_point:
            g.add((dataset, DCAT.contactPoint, self.dataset_contact_point.to_graph()))
        if self.dataset_publisher:
            g.add((dataset, DCTERMS.publisher, self.dataset_publisher.to_graph()))
        if self.dataset_metadata_provider:
            g.add((dataset, SCHEMA_ORG_NS.provider, self.dataset_metadata_provider.to_graph()))
        if self.dataset_keywords:
            for keyword in self.dataset_keywords:
                g.add((dataset, DCAT.keyword, Literal(keyword.name)))
        if self.temporal_coverage_start and self.temporal_coverage_end:
            g.add((dataset, DCTERMS.temporal, Literal(f"{self.temporal_coverage_start.isoformat()}/"
                                                      f"{self.temporal_coverage_end.isoformat()}")))
        if self.temporal_resolution:
            # TODO: temporal resolution should be a xsd:duration
            g.add((dataset, DCAT.temporalResolution, Literal(self.temporal_resolution)))
        if self.dataset_spatial_coverage:
            g.add((dataset, DCTERMS.spatial, VSL[str(self.dataset_spatial_coverage.location_id)]))
        if self.spatial_resolution:
            g.add((dataset, DCAT.spatialResolutionInMeters, Literal(self.spatial_resolution)))
        if self.dataset_license:
            g.add((dataset, DCTERMS.license, VSLD[str(self.dataset_license.dataset)]))
        if self.access_rights:
            # TODO: accessRights should be dcterms:RightsStatement
            g.add((dataset, DCTERMS.accessRights, Literal(self.access_rights)))
        if self.dataset_catalog:
            g.add((dataset, DCAT.catalog, self.dataset_catalog.to_graph()))
        if self.dataset_themes:
            for theme in self.dataset_themes:
                g.add((dataset, DCAT.theme, VSDT[str(theme.data_theme_id)]))
        if self.modified:
            g.add((dataset, DCTERMS.modified, Literal(self.modified)))
        if self.taxonomic_coverage:
            g.add((dataset, EML_COV_NS.taxonomicCoverage, Literal(self.taxonomic_coverage)))
        if self.landing_page:
            g.add((dataset, DCAT.landingPage, Literal(self.landing_page)))
        if self.public_id:
            g.add((dataset, DCTERMS.identifier, Literal(self.public_id)))
        return g

    def rdf_serialize(self, out_format="json-ld"):
        f"""
        Runs the serialize function of RDFlib

        @param out_format: default output is json-ld other possibilities are: {GRAPH_PERSIST_HELP_TEXT}

        @return:
        """
        return self.to_graph().serialize(format=out_format)

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
    dataset = relationship("Dataset", foreign_keys=[distribution_dataset_id])

    title = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    download_url = Column(String(255), nullable=True)
    access_url = Column(String(255), nullable=True)

    distribution_mediatype_id = Column(Integer, ForeignKey('MediaType.mediatype_id'))
    distribution_format = relationship("MediaType", foreign_keys=[distribution_mediatype_id])

    distribution_license_id = Column(Integer, ForeignKey('LicenseDocument.license_document_id'))
    distribution_license = relationship("LicenseDocument", foreign_keys=[distribution_license_id])

    distribution_checksum_id = Column(Integer, ForeignKey('Checksum.checksum_id'))
    distribution_checksum = relationship("Checksum", foreign_keys=[distribution_checksum_id])

    def to_graph(self):
        """

        @return: Agent object in RDFlib graph format
        """
        g = Graph()
        # Add namespaces to the graph
        g.bind("foaf", FOAF)
        g.bind("vp_agent", VSA)

        # Create a foaf:Agent instance
        distribution = VSD[str(self.distribution_id)]

        # Add properties to the agent
        g.add((distribution, RDF.type, DCAT.Distribution))
        g.add((distribution, DCTERMS.title, Literal(self.title)))
        if self.description:
            g.add((distribution, DCTERMS.description, Literal(self.description)))
        if self.download_url:
            g.add((distribution, DCAT.downloadURL, Literal(self.download_url)))
        if self.access_url:
            g.add((distribution, DCAT.accessURL, Literal(self.access_url)))
        if self.distribution_format:
            g.add((distribution, DCTERMS.format, self.distribution_format.to_graph()))
        if self.distribution_license:
            g.add((distribution, DCTERMS.license, self.distribution_license.to_graph()))
        if self.distribution_checksum:
            g.add((distribution, SPDX.Checksup, self.distribution_checksum.to_graph()))

        return g

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

    def to_graph(self):
        """

        @return: Agent object in RDFlib graph format
        """
        g = Graph()
        # Add namespaces to the graph
        g.bind("foaf", FOAF)
        g.bind("vp_agent", VSA)

        # Create a foaf:Agent instance
        data_service = VSDS[str(self.dataservice_id)]

        # Add properties to the agent
        g.add((data_service, RDF.type, DCAT.DataService))
        g.add((data_service, DCTERMS.title, Literal(self.title)))
        if self.description:
            g.add((data_service, DCTERMS.description, Literal(self.description)))
        if self.endpoint_url:
            g.add((data_service, DCAT.endpointURL, Literal(self.endpoint_url)))
        if self.access_url:
            g.add((data_service, DCAT.Catalog, self.catalog.to_graph()))
        if self.distribution_format:
            g.add((data_service, DCTERMS.LicenseDocument, self.license.to_graph()))
        if self.distribution_license:
            g.add((data_service, DCTERMS.format, self.format.to_graph()))

        return g


class MediaType(Base):
    """A set of media types from the DCAT-AP vocabulary."""

    __tablename__ = 'MediaType'

    mediatype_id = Column(Integer, primary_key=True, nullable=False)

    extension = Column(String(10), nullable=True)
    code = Column(String(10), nullable=True, unique=True)
    media_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    def to_graph(self):
        """
        TODO: some are a bit guessed
        @return: MediaType object in RDFlib graph format
        """
        g = Graph()
        # Add namespaces to the graph
        g.bind("foaf", FOAF)
        g.bind("vp_agent", VSA)

        # Create a foaf:Agent instance
        media_type = VSMT[str(self.mediatype_id)]

        # Add properties to the agent
        g.add((media_type, RDF.type, DCTERMS.MediaType))

        if self.description:
            g.add((media_type, DCTERMS.description, Literal(self.description)))
        if self.extension:
            g.add((media_type, DCTERMS.extent, Literal(self.extension)))
        if self.code:
            g.add((media_type, DCTERMS.format, self.catalog.to_graph()))
        if self.media_type:
            g.add((media_type, DCTERMS.type, self.license.to_graph()))

        return g

    def __str__(self):
        return self.extension


class LicenseDocument(Base):
    """A set of licenses from the DCAT-AP vocabulary."""

    __tablename__ = 'LicenseDocument'

    license_document_id = Column(Integer, primary_key=True, nullable=False)

    # Recommended properties
    @property
    def type(self):
        """

        :return: url or label
        """
        return self.url_general or self.label

    label = Column(String(255), nullable=True)
    code = Column(String(255), nullable=False)
    url_general = Column(String(255), nullable=True)
    url_document = Column(String(255), nullable=True)

    def __str__(self):
        if self.label and self.code:
            return f"{self.name} <{self.mbox}>"
        if self.code:
            return self.code
        if self.label:
            return self.label
        return ""

    def web(self):
        """

        :return: a web viewable version of a license
        """
        if self.label and self.code:
            return f"<a href='{self.name}>{self.mbox}</a>"
        if self.code:
            return self.code
        if self.label:
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
        Add or Update a keyword, Add a keyword to the database, if it does not yet exist.


        :param keyword_names:
        :param keyword_ids: TODO: does this need to stay?
        :param persist: default True, if persist false is selected, just the data model will be built, but nothing will
                    be saved in database
        :return:
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
    def add_or_update_location(cls, geometry=None, persist=True):
        """
        Add or update a Location object to the database, using a geometry

        An Agent can be a Person or an Organization

        :param geometry:
        :param persist:
        :return:
        """
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

    @classmethod
    def from_shapefile(cls, shapefile, persist=True):
        """
        Create a Location object from a zipped shapefile
        :param shapefile: ARCgis shapefile in zip format
        :param persist: just create object or persist in database

        TODO: Warning the input size of the shapefile is not checked, shapes larger then N should be simplefied

        :return: Location object
        """
        try:
            zipfile_ob = zipfile.ZipFile(shapefile)
            tmpdirname = None
            with tempfile.TemporaryDirectory() as tmpdirname:
                shape_files = []
                for zipped_shape_file in zipfile_ob.filelist:
                    if not zipped_shape_file.is_dir():
                        extracted_shape_file = f'{tmpdirname}/{zipped_shape_file.filename.split("/")[-1]}'
                        with open(extracted_shape_file, 'wb') as f:
                            f.write(zipfile_ob.read(zipped_shape_file.filename))
                            shape_files.append(extracted_shape_file)

                shape_file = [shp for shp in shape_files if shp.endswith(".shp")][0]

                shape_dataframe = gpd.read_file(shape_file)
                shape_dataframe = shape_dataframe.to_crs(4326)
                geoms = []
                for idx, record in shape_dataframe.iterrows():
                    # Get the geometry from the record
                    geometry = shape(record['geometry'])
                    geoms.append(geometry)
                    spatial_coverage_wkb = GeometryCollection(geoms)
                    spatial_coverage_wkt = shapely.to_wkt(spatial_coverage_wkb)

                    # To location
                    return cls.add_or_update_location(geometry=spatial_coverage_wkt, persist=persist)

        finally:
            if os.path.exists(tmpdirname):
                shutil.rmtree(tmpdirname)

    def to_shape(self, field="geometry", to="wkt"):
        """
        Print the Location as a shape

        :param field: the field of Location can be either [geometry, bbox or centroid]
        :param to: output format can be either [geogson or wkt]
        :return:
        """
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

