from datetime import datetime
import random

from faker import Faker
import shapely
from shapely.geometry import GeometryCollection, box

from application.models import (
    REVIEW_ACTOR_SYSTEM,
    REVIEW_STATUS_ACCEPTED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_REVISION,
    REVIEW_STATUS_SUBMITTED,
    LicenseDocument,
    Location,
    Agent,
    Dataset,
    Keyword,
    Catalog,
    DataTheme,
)
from application.workflow import initialize_reviewable, transition_reviewable


MOCK_TIMESTAMP = datetime(2026, 1, 1, 12, 0)
SUPPORTED_REVIEW_STATUSES = {
    REVIEW_STATUS_ACCEPTED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_REVISION,
    REVIEW_STATUS_SUBMITTED,
}
fake = Faker()


class MockObjects:
    """Build valid, reusable ORM fixtures for dataset behavior tests.

    Use this factory when a test needs an ordinary dataset aggregate whose
    metadata is incidental to the behavior under test. Tests for invalid
    constraints, historical migrations, form parsing, workflow initialization,
    or lightweight protocol stubs should construct their specialized inputs
    directly instead. Use ``create_fake_dataset`` when varied, realistic-looking
    records are needed for bulk data generation rather than repeatable assertions.
    """

    def __init__(self, db_session=None):
        if db_session is None:
            self.db_session = DBSessionMock()
        else:
            self.db_session = db_session

    def create_mock_dataset(
        self,
        dataset_id_prefix="1",
        status=REVIEW_STATUS_ACCEPTED,
        review_comment=None,
        *,
        persist=True,
        commit=True,
        changed_at=None,
        include_related=True,
        dataset_overrides=None,
        actor_mode=REVIEW_ACTOR_SYSTEM,
    ):
        """Create a valid dataset aggregate with controllable persistence.

        ``persist=False`` returns a transient aggregate and never touches the
        configured session. ``commit=False`` adds a persistent fixture to the
        session but leaves flushing and transaction completion to the caller.
        """
        if status not in SUPPORTED_REVIEW_STATUSES:
            raise ValueError(f"Unsupported fixture review status {status!r}.")

        timestamp = changed_at or MOCK_TIMESTAMP
        fixture_key = str(dataset_id_prefix).lower().replace(" ", "-")
        values = {
            "modified": timestamp,
            "release_date": timestamp,
            "language": "EN",
            "title": f"Mock dataset - {dataset_id_prefix}",
            "description": "Metadata for a reusable dataset test fixture.",
            "resource_type": "dataset",
            "temporal_coverage_start": datetime(2020, 1, 1),
            "temporal_coverage_end": datetime(2021, 1, 1),
            "temporal_resolution": "P1D",
            "spatial_resolution": "100 m",
            "taxonomic_coverage": "Plants",
            "access_rights": "open access",
            "landing_page": f"https://example.org/datasets/{fixture_key}",
            "public_id": f"DS-{dataset_id_prefix}",
        }
        values.update(dataset_overrides or {})
        dataset = Dataset(**values)

        if include_related:
            dataset.creator = Agent(
                name=f"Creator {dataset_id_prefix}",
                type="Person",
                mbox=f"creator-{fixture_key}@example.org",
            )
            dataset.dataset_contact_point = Agent(
                name=f"Contact {dataset_id_prefix}",
                type="Person",
                mbox=f"contact-{fixture_key}@example.org",
            )
            dataset.dataset_publisher = Agent(
                name=f"Publisher {dataset_id_prefix}",
                type="Organisation",
                mbox=f"publisher-{fixture_key}@example.org",
            )
            dataset.dataset_metadata_provider = Agent(
                name=f"Metadata provider {dataset_id_prefix}",
                type="Person",
                mbox=f"provider-{fixture_key}@example.org",
            )
            dataset.dataset_keywords.append(Keyword(name=f"keyword-{fixture_key}"))
            dataset.dataset_spatial_coverage = Location(
                geometry=(
                    "GEOMETRYCOLLECTION (POLYGON ((5.6 51.9, 5.7 51.9, "
                    "5.7 52, 5.6 52, 5.6 51.9)))"
                ),
                bbox="POLYGON ((5.6 51.9, 5.7 51.9, 5.7 52, 5.6 52, 5.6 51.9))",
                centroid="POINT (5.65 51.95)",
            )
            dataset.dataset_license = LicenseDocument(code="CC-BY-4.0")
            dataset.dataset_catalog = Catalog(
                title=f"Mock catalog - {dataset_id_prefix}"
            )

        initialize_reviewable(
            dataset,
            actor_mode=actor_mode,
            changed_at=timestamp,
        )
        if status != REVIEW_STATUS_SUBMITTED:
            transition_comment = review_comment
            if status in {REVIEW_STATUS_REVISION, REVIEW_STATUS_REJECTED}:
                transition_comment = transition_comment or "Review feedback"
            transition_reviewable(
                dataset,
                status,
                review_comment=transition_comment,
                actor_mode=actor_mode,
                changed_at=timestamp,
            )

        self._persist_dataset(dataset, persist, commit)

        return dataset

    def create_fake_dataset(
        self,
        dataset_id_prefix="1",
        status=REVIEW_STATUS_ACCEPTED,
        review_comment=None,
        *,
        persist=True,
        commit=True,
        changed_at=None,
        include_related=True,
        dataset_overrides=None,
        actor_mode=REVIEW_ACTOR_SYSTEM,
    ):
        """Create a varied, realistic-looking dataset for bulk test data."""
        modified = changed_at or fake.date_time_between(
            start_date="-1y",
            end_date="now",
        )
        overrides = {
            "modified": modified,
            "release_date": fake.date_time_between(
                start_date="-2y",
                end_date="-1y",
            ),
            "language": random.choice(["en", "nl", "fr", "de"]),
            "title": f"{fake.catch_phrase()} - {dataset_id_prefix}",
            "description": fake.paragraph(nb_sentences=5),
            "resource_type": random.choice(
                ["Dataset", "Image Collection", "Sensor Data", "Survey Results"]
            ),
            "temporal_coverage_start": fake.date_time_between(
                start_date="-5y",
                end_date="-3y",
            ),
            "temporal_coverage_end": fake.date_time_between(
                start_date="-2y",
                end_date="now",
            ),
            "temporal_resolution": random.choice(["P1D", "P1W", "P1M", "P1Y"]),
            "spatial_resolution": random.choice(
                ["1m", "10m", "100m", "1km", "Global", "Local"]
            ),
            "taxonomic_coverage": random.choice(
                [
                    "Mammals",
                    "Birds",
                    "Insects",
                    "Plants",
                    "Fungi",
                    "Bacteria",
                    "N/A",
                ]
            ),
            "access_rights": random.choice(["OPEN", "RESTRICTED", "EMBARGOED"]),
            "landing_page": fake.url(),
            "public_id": f"DS-{dataset_id_prefix}-{fake.uuid4()[:8].upper()}",
        }
        overrides.update(dataset_overrides or {})
        dataset = self.create_mock_dataset(
            dataset_id_prefix,
            status=status,
            review_comment=review_comment,
            persist=False,
            changed_at=changed_at or overrides["modified"],
            include_related=False,
            dataset_overrides=overrides,
            actor_mode=actor_mode,
        )

        if include_related:
            dataset.creator = Agent(
                name=fake.name(),
                type="Person",
                mbox=fake.email(),
            )
            dataset.dataset_contact_point = Agent(
                name=fake.name(),
                type="Person",
                mbox=fake.email(),
            )
            dataset.dataset_publisher = Agent(
                name=fake.company(),
                type="Organisation",
                mbox=fake.email(),
            )
            dataset.dataset_metadata_provider = Agent(
                name=fake.name(),
                type="Person",
                mbox=fake.email(),
            )
            for _ in range(random.randint(1, 3)):
                dataset.dataset_keywords.append(Keyword(name=fake.word()))

            center_lon = 5.67 + random.uniform(-0.5, 0.5)
            center_lat = 51.97 + random.uniform(-0.5, 0.5)
            half_width = random.uniform(0.01, 0.05)
            polygon = box(
                center_lon - half_width,
                center_lat - half_width,
                center_lon + half_width,
                center_lat + half_width,
            )
            geometry = GeometryCollection([polygon])
            dataset.dataset_spatial_coverage = Location(
                geometry=shapely.to_wkt(geometry),
                bbox=shapely.to_wkt(polygon),
                centroid=shapely.to_wkt(geometry.centroid),
            )
            dataset.dataset_license = LicenseDocument(
                code=random.choice(["CC-BY-4.0", "CC0-1.0", "MIT", "ODC-BY"])
            )
            dataset.dataset_catalog = Catalog(
                title=random.choice(
                    [
                        "General Data Catalog",
                        "Environmental Data Hub",
                        "Research Archive",
                    ]
                )
            )

        self._persist_dataset(dataset, persist, commit)
        return dataset

    def _persist_dataset(self, dataset, persist, commit):
        if persist:
            self.db_session.add(dataset)
            if commit:
                self.db_session.commit()

    def generate_datasets(self, number=10, dataset_id_prefix=""):
        """
        Generate a specified number of mock datasets.

        This method creates a list of realistic datasets by repeatedly calling
        :meth:`self.create_fake_dataset`. It prints progress messages
        during the generation process.

        :param number: The number of mock datasets to generate. Defaults to 10.
        :type number: int, optional
        :param dataset_id_prefix: a prefix to add
        :returns: A list containing the generated mock dataset objects.
        :rtype: list
        """

        mock_datasets = []
        print(f"Generating {number} mock datasets...")
        for i in range(1, number+1):
            dataset = self.create_fake_dataset(f"ds-{dataset_id_prefix}-{i}")
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

    def __init__(self):
        self._current_query_cls = None
        self._agents = {}
        self._locations = {}
        self._keywords = {}
        self._datatypes = {}
        self._licenses = {}
        self._catalogs = {}
        self._datasets = {}

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
        self._current_query_cls = cls
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
        elif cls == Dataset:
            return self._datasets.values()
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
        elif isinstance(obj, Dataset):
            if not obj.dataset_id:
                obj.dataset_id = len(self._datasets) + 1
            self._datasets[obj.dataset_id] = obj

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
