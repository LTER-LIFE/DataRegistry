from datetime import datetime, timedelta
import random

import shapely
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.polygon import Polygon

from application.models import LicenseDocument, Location, Agent, Dataset, Keyword, Catalog, DataTheme
from faker import Faker # Used for generating realistic-looking data

# Initialize Faker for generating mock data
fake = Faker()

class MockObjects:
    def __init__(self, db_session=None):
        if not db_session:
            self.db_session = DBSessionMock()
        else:
            self.db_session = db_session

    # Function to create a single mock dataset
    def create_mock_dataset(self, dataset_id_prefix="1"):
        """
        Creates a single mock Dataset object with dynamic data.
        :param dataset_id_prefix: A prefix for the dataset to make a dataset more recognisable
        :return: Dataset
        """
        dataset = Dataset()

        dataset.modified = fake.date_time_between(start_date="-1y", end_date="now")
        dataset.release_date = fake.date_time_between(start_date="-2y", end_date="-1y")
        dataset.language = random.choice(["en", "nl", "fr", "de"])
        dataset.title = f"{fake.catch_phrase()} - {dataset_id_prefix}"
        dataset.description = fake.paragraph(nb_sentences=5)
        dataset.resource_type = random.choice(["Dataset", "Image Collection", "Sensor Data", "Survey Results"])

        # Agents
        creator_email = fake.email()
        contact_email = fake.email()
        publisher_email = fake.email()
        metadata_provider_email = fake.email()

        dataset.creator = Agent.add_or_update_agent(mbox=creator_email)
        dataset.dataset_contact_point = Agent.add_or_update_agent(mbox=contact_email)
        dataset.dataset_publisher = Agent.add_or_update_agent(mbox=publisher_email)
        dataset.dataset_metadata_provider = Agent.add_or_update_agent(mbox=metadata_provider_email)

        # Keywords
        num_keywords = random.randint(1, 3)
        for _ in range(num_keywords):
            keyword_name = fake.word()
            keyword_obj = Keyword(name=keyword_name)
            self.db_session.add(keyword_obj)
            dataset.dataset_keywords.append(keyword_obj)

        # Spatial Coverage (dynamic polygons around Wageningen, NL)
        # Wageningen coordinates: ~5.67 E, 51.97 N
        center_lon = 5.67 + random.uniform(-0.5, 0.5)
        center_lat = 51.97 + random.uniform(-0.5, 0.5)
        # convex_hull ensures a valid non-degenerate polygon (collinear points produce
        # a zero-area geometry that Elasticsearch rejects even though Shapely considers it valid)
        num_points = random.randint(4, 7)
        points = []
        for _ in range(num_points):
            lon = center_lon + random.uniform(-0.05, 0.05)
            lat = center_lat + random.uniform(-0.05, 0.05)
            points.append((lon, lat))
        polygon = Polygon(points).convex_hull
        if polygon.area == 0:
            # Fallback: a small guaranteed square around the center
            polygon = Polygon([
                (center_lon - 0.01, center_lat - 0.01),
                (center_lon + 0.01, center_lat - 0.01),
                (center_lon + 0.01, center_lat + 0.01),
                (center_lon - 0.01, center_lat + 0.01),
            ])
        geometry_wkt = shapely.to_wkt(GeometryCollection([polygon]))
        dataset.dataset_spatial_coverage = Location.add_or_update_location(geometry=geometry_wkt)

        dataset.temporal_coverage_start = fake.date_time_between(start_date="-5y", end_date="-3y")
        dataset.temporal_coverage_end = fake.date_time_between(start_date="-2y", end_date="now")
        dataset.temporal_resolution = random.choice(["P1D", "P1W", "P1M", "P1Y"]) # Daily, Weekly, Monthly, Yearly
        dataset.spatial_resolution = random.choice(["1m", "10m", "100m", "1km", "Global", "Local"])
        dataset.taxonomic_coverage = random.choice(["Mammals", "Birds", "Insects", "Plants", "Fungi", "Bacteria", "N/A"])
        dataset.access_rights = random.choice(["OPEN", "RESTRICTED", "EMBARGOED"])

        # License
        license_code = random.choice(["CC-BY-4.0", "CC0-1.0", "MIT", "ODC-BY"])
        dataset.dataset_license = LicenseDocument(code=license_code)
        self.db_session.add(dataset.dataset_license) # Add to mock session

        # Catalog
        catalog_name = random.choice(["General Data Catalog", "Environmental Data Hub", "Research Archive"])
        catalog_obj = Catalog(title=catalog_name)
        self.db_session.add(catalog_obj)
        dataset.dataset_catalog = catalog_obj

        dataset.landing_page = fake.url()
        dataset.public_id = f"DS-{dataset_id_prefix}-{fake.uuid4()[:8].upper()}"

        self.db_session.add(dataset)
        self.db_session.commit()
        self.db_session.flush()

        return dataset

    def generate_datasets(self, number=10, dataset_id_prefix=""):
        """
        Generate a specified number of mock datasets.

        This method creates a list of mock datasets by repeatedly calling
        :meth:`self.create_mock_dataset`. It prints progress messages
        during the generation process.

        :param number: The number of mock datasets to generate. Defaults to 10.
        :type number: int, optional
        :param dataset_id_prefix: a prefix to add
        :returns: A list containing the generated mock dataset objects.
        :rtype: list
        """

        mock_datasets = []
        print("Generating 10 mock datasets...")
        for i in range(1, number+1):
            dataset = self.create_mock_dataset(f"ds-{dataset_id_prefix}-{i}")
            mock_datasets.append(dataset)
            print(f"Generated Dataset {i}: {dataset.title}")
        return mock_datasets


class DBSessionMock:
    """
    A mock database session class for testing purposes.

    This class simulates basic database operations like querying, filtering,
    adding objects, and committing changes without interacting with a real
    database. It stores objects in in-memory dictionaries.

    :ivar _agents: Stores mock Agent objects, keyed by mbox.
    :vartype _agents: dict
    :ivar _locations: Stores mock Location objects, keyed by geometry WKT.
    :vartype _locations: dict
    :ivar _keywords: Stores mock Keyword objects, keyed by name.
    :vartype _keywords: dict
    :ivar _datatypes: Stores mock DataTheme objects, keyed by name.
    :vartype _datatypes: dict
    :ivar _licenses: Stores mock LicenseDocument objects, keyed by code.
    :vartype _licenses: dict
    :ivar _catalogs: Stores mock Catalog objects, keyed by name.
    :vartype _catalogs: dict
    """

    _agents = {} # To store mock agents by mbox
    _locations = {} # To store mock locations by geometry WKT
    _keywords = {} # To store mock keywords by name
    _datatypes = {} # To store mock datatypes by name
    _licenses = {} # To store mock licenses by code
    _catalogs = {} # To store mock catalogs by name

    def __init__(self):
        self._current_query_cls = None

    def query(self, cls):
        """
        Simulates a database query for a specific class.

        Returns all stored objects of the given class type. Allows chaining
        with :meth:`filter_by`.

        :param cls: The class of objects to query (e.g., Agent, Location).
        :type cls: type
        :returns: A list-like view of stored objects of the specified class,
                  or the mock session object itself to allow chaining.
        :rtype: list or :class:`DBSessionMock`
        """
        if cls == Agent:
            return self._agents.values()
        elif cls == Location:
            return self._locations.values()
        elif cls == Keyword:
            return self._keywords.values()
        elif cls == DataTheme:
            return self._datatypes.values()
        elif cls == LicenseDocument:
            return self._licenses.values()
        elif cls == Catalog:
            return self._catalogs.values()
        return self # Allow chaining for filter_by

    def filter_by(self, **kwargs):
        """
        Simulates filtering the results of the previous query.

        Supports filtering by specific attributes based on the class
        queried in the preceding :meth:`query` call.

        :param kwargs: Keyword arguments representing the filter criteria
                       (e.g., mbox='...', geometry='...', name='...', code='...').
        :type kwargs: dict
        :returns: The mock session object itself to allow chaining.
        :rtype: :class:`DBSessionMock`
        """
        if 'mbox' in kwargs:
            self._current_result = [self._agents.get(kwargs['mbox'])]
        elif 'geometry' in kwargs:
            self._current_result = [self._locations.get(kwargs['geometry'])]
        elif 'name' in kwargs and self._current_query_cls == Keyword:
            self._current_result = [self._keywords.get(kwargs['name'])]
        elif 'name' in kwargs and self._current_query_cls == DataTheme:
            self._current_result = [self._datatypes.get(kwargs['name'])]
        elif 'code' in kwargs and self._current_query_cls == LicenseDocument:
            self._current_result = [self._licenses.get(kwargs['code'])]
        elif 'name' in kwargs and self._current_query_cls == Catalog:
            self._current_result = [self._catalogs.get(kwargs['name'])]
        else:
            self._current_result = [] # No specific filter applied

        return self

    def first(self):
        """
        Simulates retrieving the first result from the filtered query.

        :returns: The first object in the current result set, or None if the
                  result set is empty.
        :rtype: object or None
        """
        return self._current_result[0] if self._current_result else None

    def add(self, obj):
        """
        Simulates adding an object to the database session.

        Objects are stored in the appropriate internal dictionary based on their type.
        Assigns dummy IDs and keys (like mbox for Agent) if they are missing.

        :param obj: The object to add (e.g., an instance of Agent, Location, etc.).
        :type obj: object
        """
        if isinstance(obj, Agent):
            if obj.mbox:
                self._agents[obj.mbox] = obj
            else: # Assign a dummy mbox if not provided
                obj.mbox = f"mock_agent_{len(self._agents) + 1}@example.com"
                self._agents[obj.mbox] = obj
            if not obj.agent_id:
                obj.agent_id = len(self._agents)
        elif isinstance(obj, Location):
            if obj.geometry:
                self._locations[obj.geometry] = obj
            if not obj.location_id:
                obj.location_id = len(self._locations)
        elif isinstance(obj, Keyword):
            if obj.name:
                self._keywords[obj.name] = obj
            if not obj.keyword_id:
                obj.keyword_id = len(self._keywords)
        elif isinstance(obj, LicenseDocument):
            if obj.code:
                self._licenses[obj.code] = obj
            if not obj.license_document_id:
                obj.license_document_id = len(self._licenses)
        elif isinstance(obj, Catalog):
            if obj.title:
                self._catalogs[obj.title] = obj
            if not obj.catalog_id:
                obj.catalog_id = len(self._catalogs)

    def commit(self):
        """
        Simulates committing changes to the database.

        In this mock, this method does nothing.
        """
        pass # No actual commit in mock

    def flush(self):
        """
        Simulates flushing changes to the database.

        In this mock, this method does nothing.
        """
        pass # No actual flush in mock


