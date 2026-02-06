""" Approval functions.

These functions support the  approval workflows for user provided datasets
-> staging into the main dataset catalog

"""


from application.database import Base, db_session
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location
from application.models import AgentStaging, KeywordStaging, CatalogStaging, ChecksumStaging, DataServiceStaging, DatasetStaging, DataThemeStaging, DistributionStaging, \
    LicenseDocumentStaging, MediaTypeStaging, LocationStaging
from application.transfer import transfer_dataset
from datetime import datetime


def approve_staged_dataset(session: db_session, dataset_id: int) -> Dataset:
    stageddataset = session.get(DatasetStaging, dataset_id)
    if not stageddataset:
        raise ValueError("Staged dataset not found.")
    #if not stageddataset.is_validated:
    #    raise ValueError("Dataset must be validated before approval.")    TODO decide whether vsalidation beyond that already implemented is required

    dataset = transfer_dataset(session, stageddataset)
    
    stageddataset.is_approved = True
    stageddataset.approved_at = datetime.utcnow()
    session.commit()
    print(f"Migrated staged dataset {stageddataset.dataset_id} to database as {dataset.dataset_id}")




