"""Tests for the YARRRML -> DCAT-AP materialization pipeline (rdf/mapping-dcat.yml).

* TestYarrrmlCompilation — pure unit tests on the generated RML. No DB needed.

* TestDcatMaterialization — creates a Dataset with the project's `MockObjects`
  helper inside a rolled-back transaction (same pattern as `test_dataset.py`),
  then calls `dataset_to_graph(dataset)` and asserts the resulting RDF graph
  matches the values that ended up on the mock dataset.
"""
import re
import unittest

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, XSD

from application.database import db_session
from rdf.build import compile_yarrrml_to_rml, dataset_to_graph
from test.base_test_case import BaseTestCase
from test.db import engine
from test.mock_objects import MockObjects

VSD = Namespace("https://lter-life-experience.org/veluwesearch/Dataset/")
VSA = Namespace("https://lter-life-experience.org/veluwesearch/Agent/")
VSC = Namespace("https://lter-life-experience.org/veluwesearch/Catalog/")
VSL = Namespace("https://lter-life-experience.org/veluwesearch/Location/")
VSLD = Namespace("https://lter-life-experience.org/veluwesearch/LicenseDocument/")


class TestYarrrmlCompilation(unittest.TestCase):
    """yatter must produce an RML mapping with the expected shape."""

    @classmethod
    def setUpClass(cls):
        cls.rml = compile_yarrrml_to_rml()

    def test_compiles_without_error(self):
        self.assertIn("a rr:TriplesMap", self.rml)

    def test_no_database_credentials_in_mapping(self):
        # yatter declares the d2rq: prefix in the header, but it must never be
        # used as a triple subject/predicate when we use python_source.
        for forbidden in ("jdbc:", "d2rq:Database", "d2rq:password", "d2rq:username", "d2rq:jdbcDSN"):
            self.assertNotIn(forbidden, self.rml, f"unexpected `{forbidden}` in RML")

    def test_covers_dcat_classes(self):
        for class_iri in (
            "dcat:Dataset",
            "dcat:Catalog",
            "dcat:Distribution",
            "foaf:Agent",
            "dct:LicenseDocument",
            "dct:Location",
            "dct:PeriodOfTime",
            "dct:MediaType",
        ):
            self.assertIn(class_iri, self.rml, f"missing class {class_iri}")

    def test_dataset_subject_template_is_iri(self):
        self.assertIn(
            'rr:template "https://lter-life-experience.org/veluwesearch/Dataset/{dataset_id}"',
            self.rml,
        )

    def test_creator_uses_join_to_agent(self):
        self.assertRegex(
            self.rml,
            re.compile(
                r"dct:creator;.*?rr:parentTriplesMap <Agent_0>;.*?"
                r'rr:child "creator_id";.*?rr:parent "agent_id"',
                re.DOTALL,
            ),
        )

    def test_temporal_coverage_creates_period_of_time(self):
        self.assertIn(
            "https://lter-life-experience.org/veluwesearch/Dataset/{dataset_id}/temporal",
            self.rml,
        )
        self.assertIn("dct:PeriodOfTime", self.rml)


class TestDcatMaterialization(BaseTestCase):
    """End-to-end: mock a Dataset, materialize, assert on resulting triples."""

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        db_session.configure(bind=self.connection, join_transaction_mode="create_savepoint")

        with self.app.app_context():
            mocks = MockObjects(db_session=db_session)
            self.ds = mocks.create_mock_dataset(dataset_id_prefix="test")
            db_session.flush()  # ensure all FK ids are assigned
            self.subject = VSD[str(self.ds.dataset_id)]
            self.graph = dataset_to_graph(self.ds)

    def tearDown(self):
        db_session.remove()
        self.transaction.rollback()
        self.connection.close()

    def test_dataset_is_dcat_dataset(self):
        self.assertIn((self.subject, RDF.type, DCAT.Dataset), self.graph)

    def test_title_and_identifier_match_mock_values(self):
        self.assertIn((self.subject, DCTERMS.title, Literal(self.ds.title)), self.graph)
        self.assertIn(
            (self.subject, DCTERMS.identifier, Literal(self.ds.public_id)),
            self.graph,
        )

    def test_dates_are_typed_xsd_datetime(self):
        objects = list(self.graph.objects(self.subject, DCTERMS.issued))
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].datatype, XSD.dateTime)

    def test_landing_page_is_iri_not_literal(self):
        obj = next(self.graph.objects(self.subject, DCAT.landingPage), None)
        self.assertIsInstance(obj, URIRef)
        self.assertEqual(str(obj), self.ds.landing_page)

    def test_creator_join_resolves_to_agent(self):
        creator_iri = VSA[str(self.ds.creator.agent_id)]
        self.assertIn((self.subject, DCTERMS.creator, creator_iri), self.graph)
        self.assertIn(
            (creator_iri, FOAF.mbox, Literal(self.ds.creator.mbox)),
            self.graph,
        )

    def test_publisher_contact_provider_license_joins(self):
        self.assertIn(
            (self.subject, DCTERMS.publisher, VSA[str(self.ds.dataset_publisher.agent_id)]),
            self.graph,
        )
        self.assertIn(
            (self.subject, DCAT.contactPoint, VSA[str(self.ds.dataset_contact_point.agent_id)]),
            self.graph,
        )
        self.assertIn(
            (self.subject, DCTERMS.license, VSLD[str(self.ds.dataset_license.license_document_id)]),
            self.graph,
        )

    def test_temporal_coverage_is_period_of_time_resource(self):
        period = VSD[f"{self.ds.dataset_id}/temporal"]
        self.assertIn((self.subject, DCTERMS.temporal, period), self.graph)
        self.assertIn((period, RDF.type, DCTERMS.PeriodOfTime), self.graph)
        start_objs = list(self.graph.objects(period, DCAT.startDate))
        end_objs = list(self.graph.objects(period, DCAT.endDate))
        self.assertEqual(len(start_objs), 1)
        self.assertEqual(len(end_objs), 1)
        self.assertEqual(start_objs[0].datatype, XSD.dateTime)
        self.assertEqual(end_objs[0].datatype, XSD.dateTime)

    def test_catalog_is_linked(self):
        catalog_iri = VSC[str(self.ds.dataset_catalog.catalog_id)]
        self.assertIn((self.subject, DCAT.catalog, catalog_iri), self.graph)
        self.assertIn(
            (catalog_iri, DCTERMS.title, Literal(self.ds.dataset_catalog.title)),
            self.graph,
        )


if __name__ == "__main__":
    unittest.main()
