"""Tests for the dataportal JSON -> DCAT-AP pipeline (rdf/mapping-dataportal.yml).

* TestDataportalYarrrmlCompilation — pure unit tests on the generated RML.

* TestDataportalMaterialization — materializes the synthetic export in
  fixture_dataportal.json (no database involved) and asserts on the triples,
  including that portal user secrets never reach the graph.
"""
import unittest
from pathlib import Path

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, XSD

from rdf.build import compile_yarrrml_to_rml
from rdf.dataportal import YARRRML_FILE, load_records, materialize_dataportal

DPD = Namespace("https://dataportal.nioo.knaw.nl/view_dataset/")
DPA = Namespace("https://dataportal.nioo.knaw.nl/user/")
DPC = Namespace("https://dataportal.nioo.knaw.nl/contributor/")
DPO = Namespace("https://dataportal.nioo.knaw.nl/org/")
SCHEMA = Namespace("https://schema.org/")
GEOSPARQL = Namespace("http://www.opengis.net/ont/geosparql#")
ORG = Namespace("http://www.w3.org/ns/org#")
NIOO_ROR = URIRef("https://ror.org/01g25jp36")

FIXTURE = Path(__file__).parent / "fixture_dataportal.json"


class TestDataportalYarrrmlCompilation(unittest.TestCase):
    """yatter must produce an RML mapping with the expected shape."""

    @classmethod
    def setUpClass(cls):
        cls.rml = compile_yarrrml_to_rml(YARRRML_FILE)

    def test_compiles_without_error(self):
        self.assertIn("a rr:TriplesMap", self.rml)

    def test_subject_template_reuses_portal_view_url(self):
        self.assertIn(
            'rr:template "https://dataportal.nioo.knaw.nl/view_dataset/{dataset_id}"',
            self.rml,
        )

    def test_no_database_credentials_in_mapping(self):
        for forbidden in ("jdbc:", "d2rq:Database", "d2rq:password", "d2rq:username"):
            self.assertNotIn(forbidden, self.rml, f"unexpected `{forbidden}` in RML")

    def test_forbidden_user_fields_never_referenced(self):
        for forbidden in ("user_access_token", "user_last_login", "is_authenticated"):
            self.assertNotIn(forbidden, self.rml, f"`{forbidden}` must not be mapped")


class TestDataportalMaterialization(unittest.TestCase):
    """End-to-end: fixture JSON in, DCAT triples out."""

    @classmethod
    def setUpClass(cls):
        cls.records = load_records(FIXTURE)
        cls.graph = materialize_dataportal(cls.records)
        cls.subject = DPD["77"]

    def test_dataset_is_dcat_dataset(self):
        self.assertIn((self.subject, RDF.type, DCAT.Dataset), self.graph)

    def test_title_and_description(self):
        self.assertIn(
            (self.subject, DCTERMS.title, Literal("Fixture GC analysis dataset")),
            self.graph,
        )
        self.assertIn(
            (
                self.subject,
                DCTERMS.description,
                Literal("A synthetic dataportal record used by the mapping tests."),
            ),
            self.graph,
        )

    def test_landing_page_is_the_portal_view_url(self):
        obj = next(self.graph.objects(self.subject, DCAT.landingPage), None)
        self.assertIsInstance(obj, URIRef)
        self.assertEqual(str(obj), "https://dataportal.nioo.knaw.nl/view_dataset/77")

    def test_upload_date_is_typed_dct_issued(self):
        objects = list(self.graph.objects(self.subject, DCTERMS.issued))
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].datatype, XSD.dateTime)

    def test_access_rights_translated_to_eu_vocabulary_term(self):
        self.assertIn(
            (self.subject, DCTERMS.accessRights, Literal("RESTRICTED")), self.graph
        )

    def test_empty_doi_produces_no_identifier(self):
        self.assertEqual(list(self.graph.objects(self.subject, DCTERMS.identifier)), [])

    def test_contact_join_resolves_to_portal_user_agent(self):
        contact_iri = DPA["9002"]
        self.assertIn((self.subject, DCAT.contactPoint, contact_iri), self.graph)
        self.assertIn((contact_iri, RDF.type, FOAF.Agent), self.graph)
        self.assertIn(
            (contact_iri, FOAF.mbox, Literal("t.contact@example.org")), self.graph
        )

    def test_depositor_maps_to_schema_provider(self):
        self.assertIn((self.subject, SCHEMA.provider, DPA["9001"]), self.graph)

    def test_keywords_are_literals_on_the_dataset(self):
        keywords = set(self.graph.objects(self.subject, DCAT.keyword))
        self.assertEqual(keywords, {Literal("methane"), Literal("compost")})

    def test_temporal_coverage_is_period_of_time(self):
        period = DPD["77/temporal"]
        self.assertIn((self.subject, DCTERMS.temporal, period), self.graph)
        self.assertIn((period, RDF.type, DCTERMS.PeriodOfTime), self.graph)
        for predicate in (DCAT.startDate, DCAT.endDate):
            objects = list(self.graph.objects(period, predicate))
            self.assertEqual(len(objects), 1)
            self.assertEqual(objects[0].datatype, XSD.dateTime)

    def test_geographic_origin_becomes_centroid_wkt(self):
        location = DPD["77/location"]
        self.assertIn((self.subject, DCTERMS.spatial, location), self.graph)
        wkt = next(self.graph.objects(location, DCAT.centroid), None)
        self.assertIsNotNone(wkt)
        self.assertEqual(str(wkt), "POINT(6.10573 51.39140)")
        self.assertEqual(wkt.datatype, GEOSPARQL.wktLiteral)

    def test_contributors_become_named_agents(self):
        alpha = DPC["a.alpha"]
        self.assertIn((self.subject, DCTERMS.contributor, alpha), self.graph)
        self.assertIn((alpha, RDF.type, FOAF.Agent), self.graph)
        self.assertIn((alpha, FOAF.name, Literal("A. Alpha")), self.graph)
        self.assertIn(
            (self.subject, DCTERMS.contributor, DPC["b.beta"]), self.graph
        )

    def test_publisher_is_research_group_with_department_expanded(self):
        group = DPO["me-fixture-group"]
        self.assertIn((self.subject, DCTERMS.publisher, group), self.graph)
        self.assertIn((group, RDF.type, FOAF.Organization), self.graph)
        self.assertIn(
            (
                group,
                FOAF.name,
                Literal("Fixture group (Microbial Ecology), Netherlands Institute of Ecology"),
            ),
            self.graph,
        )

    def test_research_group_is_unit_of_the_nioo_ror_iri(self):
        self.assertIn((DPO["me-fixture-group"], ORG.unitOf, NIOO_ROR), self.graph)
        self.assertIn((NIOO_ROR, RDF.type, FOAF.Organization), self.graph)
        self.assertIn(
            (
                NIOO_ROR,
                FOAF.name,
                Literal("Netherlands Institute of Ecology (NIOO-KNAW)"),
            ),
            self.graph,
        )

    def test_portal_user_secrets_never_reach_the_graph(self):
        serialized = self.graph.serialize(format="ntriples")
        for secret in ("SECRET-TOKEN-MUST-NOT-LEAK", "OTHER-SECRET-TOKEN", "user_access_token"):
            self.assertNotIn(secret, serialized)


if __name__ == "__main__":
    unittest.main()
