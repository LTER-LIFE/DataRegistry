""" Approval functions.

These functions support the  approval workflows for user provided datasets
-> staging into the main dataset catalog

"""


from application.database import Base, db_session
from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location
from application.models import AgentStaging, KeywordStaging, CatalogStaging, ChecksumStaging, DataServiceStaging, DatasetStaging, DataThemeStaging, DistributionStaging, \
    LicenseDocumentStaging, MediaTypeStaging, LocationStaging


def approve_staged_dataset(session: Session, dataset_id: int) -> Dataset:
    stageddataset = session.get(DatasetStaging, dataset_id)
    if not stageddataset:
        raise ValueError("Staged dataset not found.")
    if not stageddataset.is_validated:
        raise ValueError("Dataset must be validated before approval.")

    dataset = Dataset.from_staged_dataset(stdataset=stageddataset)
        
    session.add(dataset)
    stageddataset.is_approved = True
    stageddataset.approved_at = datetime.utcnow()
    session.commit()
    session.flush()
    
    return dataset


