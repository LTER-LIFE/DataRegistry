from elasticsearch import Elasticsearch

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
    "dataset_spatial_covarage": {"type": "object", "properties": {"geometry": {"type": "geo_shape"},  # Add geometry
        "bbox": {"type": "geo_shape"},  # Add bbox
        "centroid": {"type": "geo_point"}  # Add centroid
    }}, "spatial_resolution": {"type": "keyword"},
    "dataset_license": {"type": "object", "properties": {"license_document_id": {"type": "integer"}}},
    "access_rights": {"type": "keyword"},
    "dataset_catalog": {"type": "object", "properties": {"catalog_id": {"type": "integer"}}},
    "modified": {"type": "date"}, "taxonomic_coverage": {"type": "text"}, "landing_page": {"type": "keyword"},
    "public_id": {"type": "keyword"}}}

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
    Index document, when a dataset object is Created or Updated it will be added to the index
    """
    if not es:
        validate_index()
    es_doc_id = object.to_dict().get(object.__mapper__.primary_key[0].name)
    es.index(index=INDEX_NAME, id=es_doc_id, document=object.to_dict())

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