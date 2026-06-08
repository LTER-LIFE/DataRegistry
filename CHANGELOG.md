# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Create a changelog following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- Create CONTRIBUTING.md, a document with guidelines for contributing to this project
- Show confirmation modal when an item is added to the download list
- Add `area` URL parameter to Dataset Page, e.g. `/datasets?area=veluwe`

### Changed

- Show "remove from download list" when an item is already in the download list
- Change Area filter on Datasets page to a select field

### Fixed

- Refactor deprecated SQLAlchemy `Query.get` API


## [0.6.0] - 2026-03-30
Version demonstrated at the LTER-LIFE semi-annual meeting in March/April 2026

### Added

- Add dataset detail page
- Show loading indicator when LLM-based metadata harvester is in progress
- Add delete option to staging, so that an admin can delete a submitted record

### Changed

- Rename Shopping cart to Download list
- Update logo link to new homepage (https://lter-nl.nl/en/data)

### Fixed

- Fix bug in map view and unfiltered tab view resulting in only 10 records displayed
- Fix bug when editing a record in the staging module resulting in spatial resolution being a mandatory field
- Replace mentions of Veluwe Metadata Portal by LTER-NL Data Registry in Register dataset form and mentions of Veluwe by Netherlands in instructions and about pages


## [0.5.0] - 2026-02-09
Version demonstrated at the Netherlands Annual Ecology Meeting (NAEM) 10 & 11 February 2026

### Breaking changes

- Implement Docker to containerise project
- Replace conda by uv as package manager
- Drop support for SQLite

### Added

- Add Apache-2.0 license
- Implement the [LTER-LIFE's LLM-based metadata harvester service](https://github.com/LTER-LIFE/LLM-metadata-harvester-service) to pre-fill the Register dataset form
- Add staging and approval logic, so that metadata records submitted by a user are first checked and approved by an admin
- Add reference to LTER-LIFE website in footer

### Changed

- Align design with [LTER-NL website](https://lter-nl.nl/)
- Update layout and design of Table page
- Change application name to LTER-NL Data Registry and change logo


## [0.4.0] - 2025-09-24
Version demonstrated at the LTER-LIFE semi-annual meeting in September 2025

### Breaking changes

- Implement Elasticsearch search engine so that users can search and filter through the metadata records

### Added

- Add cart export functionality so that users can export metadata records (as json-ld files)

### Changed

- Fix height of the map in Table page

### Fixed

- Fix bug in parsing GeoJSON in map view
- Fix typo in data model (i.e., spatial coverage)
- Make sure (Multi)Polygon geometries are compliant with GeoJSON winding order


## [0.3.0] - 2025-03-24
Version demonstrated at the LTER-LIFE semi-annual meeting in March 2025

### Added

- Implement SURF Research Access Management (SRAM) for login and authentication 
- Add options to edit and delete metadata records, only for users registered in the SRAM admin group
- Add shapefile input option for spatial coverage in Register dataset form
- Add User instruction page
- Add functionality to convert a record to RDF graph
- Implement alembic, a database migrations tool to upgrade and downgrade database versions

### Changed

- Set end date in Register dataset form to optional 

### Fixed

- Fix missing keywords in database
- Fix bug in Register dataset form related to creator's email address resulting in empty mailto field in table view


## [0.2.0] - 2024-12-17
Version demonstrated at the 2nd Veluwe Research Community Meeting (2024-12-19)
Since this version the application is available at https://lter-life-experience.org

### Added

- Add Table page, a tabular view of metadata records
- Add About page
- Implement DCAT-AP as data model
- Add support for SQLite

### Changed

- Update map view and Register dataset form to match new data model


## [0.1.0] - 2024-08-26
Initial release of the Veluwe Metadata Portal

### Added

- Implement Flask for the web app
- Implement PostgreSQL for the database
- Add map view in which users can zoom in on an area of interest and retrieve information on the data that is available
- Add pop-up window to map with title, description, keywords and button to indicate the spatial coverage of a record
- Add registration form with which users can register a dataset in the portal
