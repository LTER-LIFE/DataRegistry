"""
Logic to transfer data from staging to main database, including transfer of relations
"""

from application.database import Base, db_session

from application.models import Agent, Keyword, Catalog, Checksum, DataService, Dataset, DataTheme, Distribution, \
    LicenseDocument, MediaType, Location
from application.models import AgentStaging, KeywordStaging, CatalogStaging, ChecksumStaging, DataServiceStaging, DatasetStaging, DataThemeStaging, DistributionStaging, \
    LicenseDocumentStaging, MediaTypeStaging, LocationStaging


"""
Transfer entity catalogs from staging to main tables avoiding dupicates.
This ensures that releavnt relations between entities recorded
in the staging table are correctly transfered to the main tables. 
"""


# ---------------------------------------------------------
# Helper caches to prevent duplicates
# ---------------------------------------------------------
agent_cache = {}
keyword_cache = {}
theme_cache = {}
location_cache = {}
license_cache = {}
catalog_cache = {}


# ---------------------------------------------------------
# Transfer AgentStaging → Agent
# ---------------------------------------------------------
def get_or_create_agent(session: db_session, staging_agent: AgentStaging):
    #TODO this was in place meiert,
    if staging_agent is None:
        return None

    if staging_agent.agent_id in agent_cache:
        return agent_cache[staging_agent.agent_id]

    # Define uniqueness rule — adapt this to your schema
    agent = session.query(Agent).filter_by(
        name=staging_agent.name
    ).first()

    if not agent:
        agent = Agent(
            name=staging_agent.name,
            type=staging_agent.type,
            mbox=staging_agent.mbox
        )
        session.add(agent)
        session.flush()

    agent_cache[staging_agent.agent_id] = agent
    return agent


# ---------------------------------------------------------
# Transfer KeywordStaging → Keyword
# ---------------------------------------------------------
def get_or_create_keyword(session: db_session, staging_keyword: KeywordStaging):
    #TODO please check meiert
    if not staging_keyword:
        return None

    if staging_keyword.keyword_id in keyword_cache:
        return keyword_cache[staging_keyword.keyword_id]

    keyword = session.query(Keyword).filter_by(
        name=staging_keyword.name
    ).first()

    if not keyword:
        keyword = Keyword(
            name=staging_keyword.name,
            slug=staging_keyword.slug
        )
        session.add(keyword)
        session.flush()

    keyword_cache[staging_keyword.keyword_id] = keyword
    return keyword


# ---------------------------------------------------------
# Transfer DataThemeStaging → DataTheme
# ---------------------------------------------------------
def get_or_create_theme(session: db_session, staging_theme: DataThemeStaging):
    #TODO pleas check meiert
    if not staging_theme:
        return None

    if staging_theme.theme_id in theme_cache:
            return theme_cache[staging_theme.theme_id]

    theme = session.query(DataTheme).filter_by(
        code=staging_theme.code
    ).first()

    if not theme:
        theme = DataTheme(
            code=staging_theme.code,
            label=staging_theme.label,
            description=staging_theme.description
        )
        session.add(theme)
        session.flush()

    theme_cache[staging_theme.theme_id] = theme
    return theme


# ---------------------------------------------------------
# Transfer LocationStaging → Location
# ---------------------------------------------------------
def get_or_create_location(session: db_session, staging_location: LocationStaging):
    if staging_location.location_id in location_cache:
        return location_cache[staging_location.location_id]

    location = session.query(Location).filter_by(
        geometry=staging_location.geometry
    ).first()

    if not location:
        location = Location(
            geometry=staging_location.geometry,
            bbox=staging_location.bbox,
            centroid=staging_location.centroid
        )
        session.add(location)
        session.flush()

    location_cache[staging_location.location_id] = location
    return location


# ---------------------------------------------------------
# Transfer LicenseDocumentStaging → LicenseDocument
# ---------------------------------------------------------
def get_or_create_license(session: db_session, staging_license: LicenseDocumentStaging):
    #TODO: please check meiert
    if not staging_license:
        return None

    if staging_license.license_document_id in license_cache:
            return license_cache[staging_license.license_document_id]

    license_doc = session.query(LicenseDocument).filter_by(
        code=staging_license.code
    ).first()

    if not license_doc:
        license_doc = LicenseDocument(
            code=staging_license.code,
            label=staging_license.label,
            url_general=staging_license.url_general,
            url_document=staging_license.url_document
        )
        session.add(license_doc)
        session.flush()

    license_cache[staging_license.license_document_id] = license_doc
    return license_doc


# ---------------------------------------------------------
# Transfer CatalogStaging → Catalog
# ---------------------------------------------------------
#TODO This is recursive with datasets. Still to be implemented. ADDITIONAL ISSUE: A dataset may be present in
# multiple catalogs. This is currenlty not supported
def get_or_create_catalog(session: db_session, staging_catalog: CatalogStaging):
    if staging_catalog is not None:
        if staging_catalog.catalog_id in catalog_cache:
            return catalog_cache[staging_catalog.catalog_id]

        catalog = session.query(Catalog).filter_by(
            name=staging_catalog.title
        ).first()

        if not catalog:
            catalog = Catalog(title=staging_catalog.title,
                         applicable_legislation=staging_catalog.applicable_legislation,
                         contact_point=staging_catalog.contact_point,
                         description=staging_catalog.description,
                         homepage=staging_catalog.homepage,
                         creator=get_or_create_agent(session,staging_catalog.creator),
                         publisher=get_or_create_agent(session,staging_catalog.publisher),
                         license=get_or_create_license(session,staging_catalog.license)
            )
            catalog.themes = [get_or_create_theme(session,t) for t in staging_catalog.themes]
            session.add(catalog)
            session.flush()

        catalog_cache[staging_catalog.catalog_id] = catalog
    else:
        catalog = None
    return catalog


# ---------------------------------------------------------
# Transfer DatasetStaging → Dataset
# ---------------------------------------------------------
def transfer_dataset(session: db_session, staged_dataset: DatasetStaging):
    dataset = Dataset(
        release_date=staged_dataset.release_date,
        language=staged_dataset.language,
        title=staged_dataset.title,
        description=staged_dataset.description,
        resource_type=staged_dataset.resource_type,

        creator=get_or_create_agent(session, staged_dataset.creator),
        dataset_contact_point=get_or_create_agent(session, staged_dataset.dataset_contact_point),
        dataset_publisher=get_or_create_agent(session, staged_dataset.dataset_publisher),
        dataset_metadata_provider=get_or_create_agent(session, staged_dataset.dataset_metadata_provider),

        temporal_coverage_start=staged_dataset.temporal_coverage_start,
        temporal_coverage_end=staged_dataset.temporal_coverage_end,
        temporal_resolution=staged_dataset.temporal_resolution,
        spatial_resolution=staged_dataset.spatial_resolution,

        dataset_spatial_coverage=get_or_create_location(session, staged_dataset.dataset_spatial_coverage),
        dataset_license=get_or_create_license(session, staged_dataset.dataset_license),
        access_rights=staged_dataset.access_rights,
        dataset_catalog=get_or_create_catalog(session, staged_dataset.dataset_catalog),

        modified=staged_dataset.modified,
        taxonomic_coverage=staged_dataset.taxonomic_coverage,
        landing_page=staged_dataset.landing_page,
        public_id=staged_dataset.public_id,
    )

    # Many-to-many relationships
    dataset.dataset_keywords = [
        get_or_create_keyword(session, k) for k in staged_dataset.dataset_keywords
    ]

    dataset.dataset_themes = [
        get_or_create_theme(session, t) for t in staged_dataset.dataset_themes
    ]

    session.add(dataset)
    return dataset





