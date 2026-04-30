# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-02-09

### Added

- Add Apache-2.0 license
- Implement Docker to containerise project
- Implement the [LTER-LIFE's LLM-based metadata harvester service](https://github.com/LTER-LIFE/LLM-metadata-harvester-service) to pre-fill a metadata registration form
- Add staging and approval logic to the database, so that metadata records submitted by a user are first checked and approved by an admin before transferred to the database

### Changed

- Replace SQLite by PostgreSQL
- Update layout and design of table view
- Change portal name to LTER-NL Data Registry and change logo
- Align design with [LTER-NL website](https://lter-nl.nl/)

## [0.4.0] - 2025-09-24

### Added

- Implement Elasticsearch search engine so that users can search and filter through the metadata records
- Add cart export functionality so that users can export metadata records (as json-ld files)

### Fixed

- Fix bug in parsing geoJSON in map view
- Fix typo in data model (i.e., spatial coverage)
- Fix height of the map in table view
- Fix bug with multipolygon geometries

## [0.3.0] - 2025-03-24

### Added

- Implement SURF Research Access Management (SRAM) for login and authentication 
- Add options to edit and delete metadata records, only for users registered in the SRAM admin group
- Add shapefile input option for spatial coverage in registration form
- Add user instruction page
- Add database functionality to convert a record to RDF graph

### Changes

- Set end date in form to optional 
- Re-implement alembic, a database migrations tool to upgrade and downgrade database versions

### Fixed

- Fix missing keywords in database
- Fix bug in form related to creator's email address resulting in empty mailto field in table view

## [0.2.0] - 2024-12-17

### Added

- Deploy on LTER-LIFE Experience server (https://lter-life-experience.org)
- Add tabular view of metadata records
- Add about page
- Implement DCAT-AP as data model

### Changed

- Update map view and metadata form to match new data model
- Replace PostgreSQL by SQLite

## [0.1.0] - 2024-08-26

### Added

- Initial release of the Veluwe Metadata Portal, a metadata registry based on PostgreSQL and Flask