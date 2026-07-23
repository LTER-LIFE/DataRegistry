"""Compile YARRRML to RML and materialize triples with morph-kgc.

The YARRRML spec references abstract source names (datasets, agents, ...).
Data is loaded as SQLAlchemy model instances and passed to morph-kgc as an
in-memory `python_source` dict — no DB connection details live in the YAML.

Usage as a CLI:
    python -m rdf.build               # writes rdf/output.ttl from the live DB
    python -m rdf.build --print       # also prints the head of the output

Usage as a library (e.g. from tests):
    from application.models import Agent, Dataset
    from rdf.build import materialize_from_models
    alice = Agent(agent_id=1, name="Alice", mbox="alice@example.org")
    ds = Dataset(dataset_id=1, title="...", creator_id=1, ...)
    graph = materialize_from_models(datasets=[ds], agents=[alice])
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

import morph_kgc
import pandas as pd
import shapely
import sqlalchemy as sa
import yatter
from geoalchemy2.shape import to_shape
from rdflib import Graph
from ruamel.yaml import YAML
from sqlalchemy import func, select

from application.database import db_session
from application.models import (
    Agent,
    Catalog,
    Dataset,
    Distribution,
    LicenseDocument,
    Location,
    MediaType,
)

ROOT = Path(__file__).resolve().parent
YARRRML_FILE = ROOT / "mapping-dcat.yml"
RML_FILE = ROOT / "mapping-dcat.rml.ttl"
CONFIG_FILE = ROOT / "config.ini"

# morph-kgc detects in-memory Python sources by spotting a `{key}` literal as
# the rml:source value, but yatter emits the in-memory source as an
# sd:DatasetSpecification bnode whose sd:name morph-kgc's SPARQL does not
# unwrap. We inline the bnode into the literal form.
_SD_SOURCE_RE = re.compile(
    r"rml:source\s*\[\s*a\s+sd:DatasetSpecification;\s*sd:name\s+\"([^\"]+)\";\s*\];",
    re.MULTILINE,
)


def compile_yarrrml_to_rml(yarrrml_file: Path = YARRRML_FILE) -> str:
    yaml = YAML(typ="safe")
    rml = yatter.translate(yaml.load(yarrrml_file.read_text()))
    return _SD_SOURCE_RE.sub(lambda m: f'rml:source "{{{m.group(1)}}}";', rml)


def _columns(model) -> list[str]:
    return [c.name for c in model.__table__.columns]


def _instance_row(instance, columns: list[str]) -> dict:
    row = {c: getattr(instance, c, None) for c in columns}
    # Back-fill FK columns from set relationships when the instance has not
    # been flushed yet (e.g. unit tests that build models without a session).
    mapper = sa.inspect(type(instance))
    for rel in mapper.relationships:
        if not rel.local_columns:
            continue
        related = getattr(instance, rel.key, None)
        if related is None or isinstance(related, list):
            continue
        for local_col in rel.local_columns:
            if row.get(local_col.name) is None:
                remote_col = next(iter(rel.remote_side)).name
                row[local_col.name] = getattr(related, remote_col, None)
    return row


def _location_row(loc: Location) -> dict:
    """Locations carry geometry; for RDF we want a WKT literal."""
    geom = loc.geometry
    if geom is None:
        wkt = None
    elif isinstance(geom, str):
        wkt = geom
    elif hasattr(geom, "wkt"):  # shapely Geometry
        wkt = geom.wkt
    else:  # geoalchemy2 WKBElement
        wkt = to_shape(geom).wkt
    return {"location_id": loc.location_id, "wkt": wkt}


def _instances_to_df(model, instances: Iterable) -> pd.DataFrame:
    cols = _columns(model)
    return pd.DataFrame([_instance_row(i, cols) for i in instances], columns=cols)


def _locations_to_df(instances: Iterable[Location]) -> pd.DataFrame:
    return pd.DataFrame(
        [_location_row(loc) for loc in instances], columns=["location_id", "wkt"]
    )


def materialize_from_models(
    *,
    datasets: Iterable[Dataset] = (),
    agents: Iterable[Agent] = (),
    catalogs: Iterable[Catalog] = (),
    licenses: Iterable[LicenseDocument] = (),
    locations: Iterable[Location] = (),
    media_types: Iterable[MediaType] = (),
    distributions: Iterable[Distribution] = (),
    rml_out: Path | None = None,
) -> Graph:
    """Build the RDF graph from in-memory SQLAlchemy model instances."""
    sources = {
        "datasets": _instances_to_df(Dataset, datasets),
        "agents": _instances_to_df(Agent, agents),
        "catalogs": _instances_to_df(Catalog, catalogs),
        "licenses": _instances_to_df(LicenseDocument, licenses),
        "locations": _locations_to_df(locations),
        "media_types": _instances_to_df(MediaType, media_types),
        "distributions": _instances_to_df(Distribution, distributions),
    }
    return _materialize(sources, rml_out)


def dataset_to_graph(dataset: Dataset, rml_out: Path | None = None) -> Graph:
    """Materialize a single Dataset and its related entities into a Graph."""
    agents = {
        a.agent_id: a
        for a in (
            dataset.creator,
            dataset.dataset_publisher,
            dataset.dataset_contact_point,
            dataset.dataset_metadata_provider,
        )
        if a is not None
    }
    catalogs = [dataset.dataset_catalog] if dataset.dataset_catalog else []
    licenses = [dataset.dataset_license] if dataset.dataset_license else []
    locations = [dataset.dataset_spatial_coverage] if dataset.dataset_spatial_coverage else []
    return materialize_from_models(
        datasets=[dataset],
        agents=agents.values(),
        catalogs=catalogs,
        licenses=licenses,
        locations=locations,
        rml_out=rml_out,
    )


def load_sources_from_db() -> dict[str, pd.DataFrame]:
    """Load every entity from the live database via SQLAlchemy."""
    location_rows = db_session.execute(
        select(Location.location_id, func.ST_AsText(Location.geometry).label("wkt"))
    ).all()
    return {
        "datasets": _instances_to_df(Dataset, db_session.query(Dataset).all()),
        "agents": _instances_to_df(Agent, db_session.query(Agent).all()),
        "catalogs": _instances_to_df(Catalog, db_session.query(Catalog).all()),
        "licenses": _instances_to_df(LicenseDocument, db_session.query(LicenseDocument).all()),
        "locations": pd.DataFrame(location_rows, columns=["location_id", "wkt"]),
        "media_types": _instances_to_df(MediaType, db_session.query(MediaType).all()),
        "distributions": _instances_to_df(Distribution, db_session.query(Distribution).all()),
    }


def materialize(rml_out: Path | None = None) -> Graph:
    """Materialize the RDF graph from the live database."""
    return _materialize(load_sources_from_db(), rml_out)


def _materialize(
    sources: dict[str, pd.DataFrame],
    rml_out: Path | None,
    yarrrml_file: Path = YARRRML_FILE,
) -> Graph:
    rml = compile_yarrrml_to_rml(yarrrml_file)
    rml_path = rml_out if rml_out is not None else RML_FILE
    rml_path.write_text(rml)
    config = CONFIG_FILE.read_text().replace("rdf/mapping-dcat.rml.ttl", str(rml_path))
    return morph_kgc.materialize(config, python_source=sources)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", help="print head of output")
    args = parser.parse_args()

    graph = materialize()
    out_path = ROOT / "output.ttl"
    graph.serialize(destination=str(out_path), format="turtle")
    print(f"[ok] compiled YARRRML -> {RML_FILE.relative_to(ROOT.parent)}")
    print(f"[ok] materialized {len(graph)} triples -> {out_path.relative_to(ROOT.parent)}")

    if args.print:
        lines = out_path.read_text().splitlines()[:80]
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
