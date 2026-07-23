"""Map NIOO dataportal JSON exports to DCAT-AP RDF (rdf/mapping-dataportal.yml).

The portal export is Dublin Core-based, so most fields translate directly to
the DCAT predicates already used for the registry (rdf/mapping-dcat.yml). The
JSON is flattened here into dataframes and passed to morph-kgc as
`python_source`, the same pattern rdf/build.py uses for SQLAlchemy models.

Usage as a CLI:
    python -m rdf.dataportal dataportal.json   # writes rdf/output-dataportal.ttl

Usage as a library (e.g. from tests):
    from rdf.dataportal import materialize_dataportal
    graph = materialize_dataportal([record_dict, ...])
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from rdflib import Graph

from rdf.build import ROOT, _materialize

YARRRML_FILE = ROOT / "mapping-dataportal.yml"
RML_FILE = ROOT / "mapping-dataportal.rml.ttl"

# The only portal user fields that may enter the graph. Everything else on the
# user objects (access token, login state/timestamps) must never be mapped.
_AGENT_FIELDS = ("user_id", "user_name", "user_email")

# The portal knows two access levels. Translate them to the EU access-right
# vocabulary terms the registry already uses: "NIOO Readable" (anyone with a
# NIOO account can access the primary data) is access under a condition, i.e.
# RESTRICTED; the portal's "Restricted" is tighter, i.e. NON_PUBLIC.
# Unknown values pass through unchanged.
ACCESS_RIGHTS = {
    "NIOO Readable": "RESTRICTED",
    "Restricted": "NON_PUBLIC",
}

# TODO(flimsy): the portal stores department codes; this dict only knows the
# four NIOO department codes we have seen. Unknown codes pass through raw so
# they are at least visible in the output rather than silently dropped.
DEPARTMENTS = {
    "AnE": "Animal Ecology",
    "AqE": "Aquatic Ecology",
    "ME": "Microbial Ecology",
    "TE": "Terrestrial Ecology",
}

NIOO_NAME = "Netherlands Institute of Ecology"


def _org_key(department: str, group: str) -> str:
    """Slug a portal-local org IRI key: ("ME", "Bodelier group") -> "me-bodelier-group"."""
    return "-".join(f"{department} {group}".lower().split())

_DATASET_COLUMNS = [
    "dataset_id",
    "name",
    "description",
    "upload_date",
    "start_date",
    "end_date",
    "doi",
    "access_rights",
    "contact_user_id",
    "depositor_user_id",
    "org_key",
]


def _contributor_row(dataset_id, email: str) -> dict:
    """Derive an agent from a bare email: "p.bodelier@..." -> "P. Bodelier"."""
    local_part = email.split("@")[0]
    initial, _, last_name = local_part.partition(".")
    name = f"{initial.upper()}. {last_name.capitalize()}" if last_name else local_part.capitalize()
    return {
        "dataset_id": dataset_id,
        "contributor_key": local_part,
        "name": name,
        "email": email,
    }


def load_portal_sources(records: Iterable[dict]) -> dict[str, pd.DataFrame]:
    """Flatten portal JSON records into the abstract sources of the mapping."""
    datasets, agents, keywords, locations, contributors, orgs = [], {}, [], [], [], {}
    for record in records:
        dataset_id = record["dataset_id"]
        contact = record.get("dataset_contact") or {}
        depositor = record.get("dataset_depositor") or {}
        department = (record.get("department") or "").strip()
        group = (record.get("research_group") or "").strip()
        org_key = _org_key(department, group) if group else None
        if org_key:
            unit = f"{group} ({DEPARTMENTS.get(department, department)})" if department else group
            orgs[org_key] = {
                "org_key": org_key,
                "org_name": f"{unit}, {NIOO_NAME}",
            }
        datasets.append({
            "dataset_id": dataset_id,
            "name": record.get("name"),
            "description": record.get("description"),
            "upload_date": record.get("upload_date"),
            "start_date": record.get("start_date"),
            "end_date": record.get("end_date"),
            "doi": record.get("doi") or None,
            "access_rights": ACCESS_RIGHTS.get(
                record.get("dataset_access_rights"), record.get("dataset_access_rights")
            ),
            "contact_user_id": contact.get("user_id"),
            "depositor_user_id": depositor.get("user_id"),
            "org_key": org_key,
        })
        for user in (contact, depositor):
            if user.get("user_id") is not None:
                agents[user["user_id"]] = {f: user.get(f) for f in _AGENT_FIELDS}
        for keyword in record.get("keywords") or []:
            keywords.append({
                "dataset_id": dataset_id,
                "keyword_name": keyword.get("keyword_name"),
            })
        if record.get("geographic_origin"):
            locations.append({
                "dataset_id": dataset_id,
                "wkt": record["geographic_origin"],
            })
        for email in (record.get("contributors") or "").split(","):
            if email.strip():
                contributors.append(_contributor_row(dataset_id, email.strip()))
    return {
        "portal_datasets": pd.DataFrame(datasets, columns=_DATASET_COLUMNS),
        "portal_agents": pd.DataFrame(agents.values(), columns=list(_AGENT_FIELDS)),
        "portal_keywords": pd.DataFrame(keywords, columns=["dataset_id", "keyword_name"]),
        "portal_locations": pd.DataFrame(locations, columns=["dataset_id", "wkt"]),
        "portal_contributors": pd.DataFrame(
            contributors, columns=["dataset_id", "contributor_key", "name", "email"]
        ),
        "portal_orgs": pd.DataFrame(orgs.values(), columns=["org_key", "org_name"]),
    }


def materialize_dataportal(records: Iterable[dict], rml_out: Path | None = None) -> Graph:
    """Build the RDF graph from portal JSON records (dicts)."""
    return _materialize(
        load_portal_sources(records),
        rml_out if rml_out is not None else RML_FILE,
        yarrrml_file=YARRRML_FILE,
    )


def load_records(json_path: Path) -> list[dict]:
    """Read a portal export: either a single record object or a list."""
    data = json.loads(json_path.read_text())
    return data if isinstance(data, list) else [data]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path, help="dataportal JSON export")
    parser.add_argument("--print", action="store_true", help="print head of output")
    args = parser.parse_args()

    graph = materialize_dataportal(load_records(args.json_file))
    out_path = ROOT / "output-dataportal.ttl"
    graph.serialize(destination=str(out_path), format="turtle")
    print(f"[ok] compiled YARRRML -> {RML_FILE.relative_to(ROOT.parent)}")
    print(f"[ok] materialized {len(graph)} triples -> {out_path.relative_to(ROOT.parent)}")

    if args.print:
        lines = out_path.read_text().splitlines()[:80]
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
