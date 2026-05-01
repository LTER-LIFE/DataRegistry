# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Create a changelog following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- Implement [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [0.6.0] - 2026-03-30
Version demonstrated at the LTER-LIFE semi-annual meeting in March/April 2026

### Added

- Add dataset detail page
- Add loading indicator when LLM-based metadata harvester is in progress
- Add delete option to staging, so that an admin can delete a submitted record

### Changed

- Rename shopping cart to download list
- Update logo link to new homepage (https://lter-nl.nl/en/data)

### Fixed

- Fix bug in map view and unfiltered tab view resulting in only 10 records displayed
- Fix bug when editing a record in the staging module resulting in spatial resolution being a mandatory field
- Replace mentions of Veluwe Metadata Portal by LTER-NL Data Registry in form and mentions of Veluwe by Netherlands in instructions and about pages

## [0.5.0] - 2026-02-09
Version demonstrated at the Netherlands Annual Ecology Meeting (NAEM) 10 & 11 February 2026

### Added

- Add Apache-2.0 license
- Implement the [LTER-LIFE's LLM-based metadata harvester service](https://github.com/LTER-LIFE/LLM-metadata-harvester-service) to pre-fill a metadata registration form
- Add staging and approval logic to the database, so that metadata records submitted by a user are first checked and approved by an admin before transferred to the database
- Add reference to LTER-LIFE in footer

### Changed

- Update layout and design of table view
- Change portal name to LTER-NL Data Registry and change logo
- Align design with [LTER-NL website](https://lter-nl.nl/)

### Fixed

- Implement Docker to containerise project
- Replace SQLite by PostgreSQL

## [0.4.0] - 2025-09-24
Version demonstrated at the LTER-LIFE semi-annual meeting in September 2025

### Added

- Implement Elasticsearch search engine so that users can search and filter through the metadata records
- Add cart export functionality so that users can export metadata records (as json-ld files)

### Fixed

- Fix bug in parsing geoJSON in map view
- Fix typo in data model (i.e., spatial coverage)
- Fix height of the map in table view
- Fix bug with multipolygon geometries

## [0.3.0] - 2025-03-24
Version demonstrated at the LTER-LIFE semi-annual meeting in March 2025

### Added

- Implement SURF Research Access Management (SRAM) for login and authentication 
- Add options to edit and delete metadata records, only for users registered in the SRAM admin group
- Add shapefile input option for spatial coverage in registration form
- Add user instruction page
- Add database functionality to convert a record to RDF graph

### Changes

- Set end date in form to optional 

### Fixed

- Fix missing keywords in database
- Fix bug in form related to creator's email address resulting in empty mailto field in table view
- Re-implement alembic, a database migrations tool to upgrade and downgrade database versions

## [0.2.0] - 2024-12-17
Version demonstrated at the 2nd Veluwe Research Community Meeting (2024-12-19)

### Added

- Deploy on LTER-LIFE Experience server (https://lter-life-experience.org)
- Add tabular view of metadata records
- Add about page
- Implement DCAT-AP as data model

### Changed

- Update map view and metadata form to match new data model

### Fixed

- Replace PostgreSQL by SQLite

## [0.1.0] - 2024-08-26
Initial release of the Veluwe Metadata Portal

### Added

- Add map view in which users can zoom in on an area of interest and retrieve information on the data that is available
- Add pop-up window to map with title, description, keywords and button to indicate the spatial coverage of a record
- Add registration form with which users can register a dataset in the portal

### Fixed

- Implement Flask for the web app
- Implement PostgreSQL for the database