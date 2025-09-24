from elasticsearch import Elasticsearch
from shapely.wkt import loads as wkt_loads

from config import Config

# Optional: Create the index with a mapping
# This helps Elasticsearch understand your data types for better search and analysis
MAPPING = {"properties": {"dataset_id": {"type": "integer"}, "release_date": {"type": "date"},
    "language": {"type": "keyword"}, "creator": {"type": "object",
        "properties": {"agent_id": {"type": "integer"}, "name": {"type": "text"}, "type": {"type": "text"},
            "mbox": {"type": "text"}}}, "title": {"type": "text"}, "description": {"type": "text"},
    "resource_type": {"type": "keyword"}, "dataset_contact_point": {"type": "object",
        "properties": {"agent_id": {"type": "integer"}, "name": {"type": "text"}, "type": {"type": "text"},
            "mbox": {"type": "text"}}}, "dataset_publisher": {"type": "object",
        "properties": {"agent_id": {"type": "integer"}, "name": {"type": "text"}, "type": {"type": "text"}}},
    "dataset_metadata_provider": {"type": "object",
        "properties": {"agent_id": {"type": "integer"}, "name": {"type": "text"}}},
    "dataset_keywords": {"type": "keyword"},  # Array of strings
    "temporal_coverage_start": {"type": "date"}, "temporal_coverage_end": {"type": "date"},
    "temporal_resolution": {"type": "keyword"},
    "dataset_spatial_coverage": {"type": "object", "properties": {"geometry": {"type": "geo_shape"},  # Add geometry
        "bbox": {"type": "geo_shape"},  # Add bbox
        "centroid": {"type": "geo_point"}  # Add centroid
    }}, "spatial_resolution": {"type": "keyword"},
    "dataset_license": {"type": "object", "properties": {"license_document_id": {"type": "integer"}}},
    "access_rights": {"type": "keyword"},
    "dataset_catalog": {"type": "object", "properties": {"catalog_id": {"type": "integer"}}},
    "modified": {"type": "date"}, "taxonomic_coverage": {"type": "text"}, "landing_page": {"type": "keyword"},
    "public_id": {"type": "keyword"}}}


# 1. Define the blueprint for your filters and aggregations
# This is the core of the functional approach.
FILTER_BLUEPRINTS = {
    "keyword": lambda field, value: {"term": {f"{field}.keyword": value}},
    "text": lambda field, value: {"match": {field: value}},
    "range": lambda field, gte_value, lte_value: {"range": {field: {"gte": gte_value, "lte": lte_value}}},
    "geo_shape": lambda field, geojson_shape: {
        "geo_shape": {field: {"shape": geojson_shape, "relation": "intersects"}}},
    "multi_match": lambda fields, value: {"multi_match": {"query": value, "fields": fields}},
}

AGG_BLUEPRINTS = {
    "terms": lambda field: {"terms": {"field": f"{field}.keyword"}},
    "range": lambda field, ranges: {"range": {"field": field, "ranges": ranges}},
}


INDEX_NAME = Config.ELASTIC_INDEX_NAME
es = None
def validate_index():
    global es

    # Connect to Elasticsearch
    # Replace with your Elasticsearch host and port
    if not es:
        es = Elasticsearch([Config.ELASTIC_HOST],
            basic_auth=(Config.ELASTIC_USER, Config.ELASTIC_PASSWORD),
            verify_certs=Config.ELASTIC_USE_SSL,
            ca_certs=Config.ELASTIC_CA_CERT)
        # Test connection
        if es.ping():
            print("Connected to Elasticsearch!")
        else:
            print(f"Could not connect to Elasticsearch")
            exit()

        if not es.indices.exists(index=INDEX_NAME):
            es.indices.create(index=INDEX_NAME, mappings=MAPPING)
            print(f"Index '{INDEX_NAME}' created with mapping.")
        else:
            print(f"Index '{INDEX_NAME}' already exists.")

        return es

def rebuild_index(datasets):
    """
    rebuild index
    """
    global es
    from application import db_session

    # Recreate index
    if not es:
        es = validate_index()
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, mappings=MAPPING)
        print(f"Index '{INDEX_NAME}' created with mapping.")
    else:
        es.indices.delete(index=INDEX_NAME)
        es.indices.create(index=INDEX_NAME, mappings=MAPPING)
        print(f"Index '{INDEX_NAME}' recreated.")

    # push all datasets to index
    results = []
    for dataset in datasets:
        results.append(es.index(index=INDEX_NAME, body=dataset.to_dict()))

    return results


def index_document(object):
    """
    Index document, transforming temporal_coverage_start and temporal_coverage_end
    into a single date_range field for the index.
    """
    if not es:
        validate_index()

    # Convert the database object to a dictionary
    doc = object.to_dict()
    es_doc_id = doc.get(object.__mapper__.primary_key[0].name)

    # Extract the separate dates from the document
    start_date = doc.get('temporal_coverage_start')
    end_date = doc.get('temporal_coverage_end')

    # Create the date_range field for Elasticsearch
    temporal_coverage_range = {}
    if start_date:
        temporal_coverage_range['gte'] = start_date.strftime('%Y-%m-%d')
    if end_date:
        temporal_coverage_range['lte'] = end_date.strftime('%Y-%m-%d')

    # Add the new field to the document if at least one date is present
    if temporal_coverage_range:
        doc['temporal_coverage'] = temporal_coverage_range
    else:
        # If there are no dates, you can explicitly remove the field
        # to prevent indexing an empty object
        doc.pop('temporal_coverage', None)

    # Index the modified document
    es.index(index=INDEX_NAME, id=es_doc_id, document=doc)


def delete_document(object):
    """
    Remove document, when a dataset object is Removed it will be removed from the index
    """
    if not es:
        validate_index()
    es_doc_id = object.to_dict().get(object.__mapper__.primary_key[0].name)
    es.delete(index=INDEX_NAME, id=es_doc_id, ignore=[404])


def fetch_all():
    all_documents_query = {"query": {"match_all": {}}}
    return es.search(index=INDEX_NAME, body=all_documents_query)

def query(query):

    return es.search(index=INDEX_NAME, body=query)


def build_es_query(filters):
    """
    Constructs a complete Elasticsearch query body including
    search queries and aggregations from a filters dictionary.

    :param filters: A dictionary of user filters (e.g., {'keywords': 'water', 'min_year': 2000, 'max_year': 2025})
    :return: A dictionary representing the Elasticsearch query body.
    """

    must_clauses = []

    # Keyword Search (multi_match)
    keywords = filters.get('keywords')
    if keywords:
        must_clauses.append({
            "multi_match": {
                "query": keywords,
                "fields": ["title", "description", "dataset_keywords"]
            }
        })

    # Date Range Filter
    min_year = filters.get('min_year', '0')
    max_year = filters.get('max_year', '3000')

    date_range_body = {}
    if min_year:
        date_range_body["gte"] = f"{min_year}-01-01"
    if max_year:
        date_range_body["lte"] = f"{max_year}-12-31"

    if date_range_body:
        must_clauses.append({
            "range": {
                "release_date": date_range_body
            }
        })

    # WKT Geo Search
    wkt_string = filters.get('spatial_coverage')
    if wkt_string and not wkt_string == "GEOMETRYCOLLECTION EMPTY":
        try:
            geojson_shape = convert_wkt_to_geojson(wkt_string)
            must_clauses.append({
                "geo_shape": {
                    "dataset_spatial_coverage.geometry": {
                        "shape": geojson_shape,
                        "relation": "intersects"
                    }
                }
            })
        except Exception as e:
            print(f"Error converting WKT for query: {e}")
            # Do not add the geo filter if conversion fails

    query_body = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "size": 10,
        "aggs": {
            # Aggregations for your facets can be added here
        }
    }
    print(query_body)

    return query_body


def convert_wkt_to_geojson(wkt_string):
    """
    Converts a WKT string to a GeoJSON-formatted dictionary
    that is compatible with Elasticsearch's geo_shape query.

    :param wkt_string: The WKT string (e.g., 'POLYGON((...))').
    :return: A dictionary in GeoJSON format.
    """
    try:
        # Step 1: Parse the WKT string into a Shapely geometry object
        # Use wkt_loads from shapely.wkt to handle parsing
        geom = wkt_loads(wkt_string)

        # Step 2: Get the GeoJSON-like mapping from the Shapely object
        # The .mapping property provides the required format
        geojson_mapping = geom.__geo_interface__

        return geojson_mapping

    except Exception as e:
        print(f"Error converting WKT to GeoJSON: {e}")
        # Return an empty geometry to prevent the query from failing
        return {"type": "GeometryCollection", "geometries": []}