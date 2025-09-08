|         Property          |    db_range     |          rdf Property          |          Range           | Description                                |
|:-------------------------:|:---------------:|:------------------------------:|:------------------------:|:-------------------------------------------|
|        dataset_id         |     Ineger      |       dcterms:identifier       |     Literal:Integer      |                                            |
|       release_date        |    DateTime     |         dcterms:issued         |       rdfs:Literal       | ISO 8601 Date and Time compliant string    |
|         language          |     String      |        dcterms:language        | dcterms:LinguisticSystem | ISO 639-1 (two-letter) code                |
|          creator          |      Agent      |        dcterms:creator         |        foaf:Agent        |                                            |
|           title           |     String      |         dcterms:title          |       rdfs:Literal       | project subject location time version      |
|        description        |      Text       |      dcterms:description       |       rdfs:Literal       | description of the contents of the dataset |
|       resource_type       |     String      |          dcterms:type          |       rdfs:Literal       |                                            |
|   dataset_contact_point   |      Agent      |       dcat:contactPoint        |        foaf:Agent        |                                            |
|     dataset_publisher     |      Agent      |       dcterms:publisher        |        foaf:Agent        |                                            |
| dataset_metadata_provider |      Agent      |   dcterms:metadata_provider    |        foaf:Agent        |                                            |
|     dataset_keywords      |     Keyword     |          dcat:keyword          |       rdfs:Literal       |                                            |
|  temporal_coverage_start  |    DateTime     |        dcterms:temporal        |   dcterms:PeriodOfTime   | ISO 8601 start/end                         |
|   temporal_coverage_end   |    DateTime     |        dcterms:temporal        |   dcterms:PeriodOfTime   | ISO 8601 start/end                         |
|    temporal_resolution    |    DateTime     |    dcat:temporalResolution     |       xsd:duration       |                                            |
| dataset_spatial_coverage  |    Location     |        dcterms:spatial         |     dcterms:location     |                                            |
|    spatial_resolution     |     String      | dcat:spatialResolutionInMeters |       rdfs:Literal       |                                            |
|      dataset_license      | LicenseDocument |        dcterms:license         | dcterms:licenseDocument  |                                            |
|       access_rights       |     String      |      dcterms:accessRights      | dcterms:RightsStatement  |                                            |
|          catalog          |     Catalog     |          dcat:catalog          |       dcat:Catalog       |                                            |
|      dataset_themes       |  DatasetTheme   |           dcat:theme           |       rdfs:Literal       |                                            |
|         modified          |    DateTime     |        dcterms:modified        |       rdfs:Literal       |                                            |
|    taxonomic_coverage     |     String      |   eml_cov:taxonomic_coverage   |       rdfs:Literal       |                                            |
|       landing_page        |     String      |        dcat:landingPage        |       rdfs:Literal       |                                            |
|         public_id         |     String      |         dct:identifier         |       rdfs:Literal       |                                            |


# Uitleg per property

## dataset_id
RDF Property: dcterms:identifier
RANGE: Literal:Integer
DB: Column(Integer, primary_key=True, nullable=False)


## release_date

### RDF Property:
dcterms:issued
### RANGE:
rdfs:Literal encoded using the relevant ISO 8601 Date and Time compliant string [DATETIME] and typed using
the appropriate XML Schema datatype [XMLSCHEMA11-2] (xsd:gYear, xsd:gYearMonth, xsd:date, or xsd:dateTime).

Usage note:	This property SHOULD be set using the first known date of issuance.
See also:	6.5.3 Property: listing date and 6.8.3 Property: release date

This value will be automatically generated when the form is submitted.

## language

### RDF Property:
dcterms:language

### Definition:
A language of the resource. This refers to the natural language used for textual metadata (i.e., titles,
descriptions, etc.) of a cataloged resource (i.e., dataset or service) or the textual values of a dataset distribution

### Range:
dcterms:LinguisticSystem

Resources defined by the Library of Congress (ISO 639-1) should be used If a ISO 639-1 (two-letter) code is defined for
language, then its corresponding IRI SHOULD be used

Form will contain EN and NL

## Creator
### RDF Property:
dcterms:creator

### Range:
foaf:Agent
ignKey('Agent.agent_id'))


## Title

### Definition
The name of the described dataset.
Recommended spelling for this property is: (project attribute) subject (location attribute) (time attribute)(version).
The parts in brackets are not mandatory, the others are. Abbreviations are only permitted in the title if they are also
written out, for example: “Large-scale Basic Map of the Netherlands (GBKN)”.

This property can only be iterated to display the value in a different language. See multilingualism for dealing
with different languages.

### RDF property:
dcterms:title

### Range:
rdfs:Literal

## Description
### Definition
This property contains a description of the contents of the dataset. This is preferably at least three sentences and a
maximum of one paragraph long (2000 characters). The findability of the dataset is determined, among other things, by
the quality of the description. This includes different users, colleagues, but also others, for whom the text must be
understandable.

This property can only be iterated to display the value in a different language. See multilingualism for dealing
with different languages.

### RDF property:
dcterms:description

### Range:
rdfs:Literal


## Resource type
### RDF property:
dcterms:type
### Range:
Literal

## Contact point

### RDF property:
dcat:contactPoint
### Range:
foaf:Agent


## Publisher
### RDF property:
dcterms:publischer
### Range:
foaf:Agent

## Metadata provider
### RDF property:
dcterms:metadata_provider

### Range:
foaf:Agent

## Keywords
### RDF propery:
dcat:keyword

### Range:
rdf:Literal

## Temporal range
### RDF property:
dcterms:temporal

### Range:
dcterms:PeriodOfTime

ISO 8601 start/end


## Temporal resolution
### Definition:
https://en.wikipedia.org/wiki/ISO_8601 tem
"2007-03-01T13:00:00Z/2008-05-11T15:30:00Z"

### RDF property:
dcat:temporalResolution

### Range:
xsd:duration

## Spatial coverage
### Definition:
ISO 19115 WKT!!!

### RDF Propery:
dcterms:spatial
### Range:
dcterms:location

## Spatial resolution
### RDF Properties:
dcat:spatialResolutionInMeters

### Range:
rdf:Literal

## License
### RDF Property:
dcterms:license

### Range:
dcterms:licenseDocument

## Access Rights
### RDF Property:
dcterms:accessRights

### Range:
dcterms:RightsStatement

##  Taxonimic Coverage
### RDF property:
eml:taxonomic_coverage
### Range:
rdf:Literal

## Landing page
### Definition
we will just use address for now (url)
### RDF Property:
dcat:landingPage
### Range:
foaf:Document

## Public Id
### RDF Property:
dct:identifier

### Range:
rdf:Literal
