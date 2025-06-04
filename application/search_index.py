
from elasticsearch import Elasticsearch


class SearchIndex:
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

    def __init__(self):
        INDEX_NAME = "dataset"
        # Connect to Elasticsearch
        # Replace with your Elasticsearch host and port
        es = Elasticsearch(['http://localhost:9200'],
            # api_key=("your_api_key_id", "your_api_key_secret"), # If using API keys
            basic_auth=("elasticsearch", "xtjjBkvHmYfHtXQpKPq="),  # If using basic auth
            # verify_certs=False # Use with caution in production
        )

        if not es.indices.exists(index=INDEX_NAME):
            es.indices.create(index=INDEX_NAME, mappings=SearchIndex.MAPPING)
            print(f"Index '{INDEX_NAME}' created with mapping.")
        else:
            print(f"Index '{INDEX_NAME}' already exists.")
        # Test connection
        try:
            es.ping()
            print("Connected to Elasticsearch!")
        except Exception as e:
            print(f"Could not connect to Elasticsearch: {e}")
            exit()