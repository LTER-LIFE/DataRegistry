# Ecological Metadata Portal Veluwe
By: Sander Vlugter
Internship project with NIOO-KNAW part of WUR MSc Bioinformatics programme 2024

## Set up local version
Git clone or download the repository.
Included in the repository is a yaml with the dependencies and packages.
Not included but required: (Postgre)SQL.

With (Postgre)SQL installed set up a database and fill out the .env_template file accordingly.
***Do not forget to rename .env_template to .env***

Can start the application by running app.py

## Adapting the forms & database
If the forms are no longer sufficient, to make changes to the form the database needs to be changed accordingly.
This is not done automatically, thus additional tables/columns need to be added depending on the changes.
In addition, changes need to be made to the files:
website/forms.py
    - FlaskForm AddStudy needs to be updated to include/remove fields from the form matching the database.
website/templates/add_recored.hmtl
    - function add_study needs to be updated to include/remove fields from the form matching the database.
website/models/models.py 
    - Class Catalog needs to be updated to include/remove fields from the database matching to the database design.
website/views.py
    - function addstudy() needs to be updated in the validate on submit fields according to the changes.


## Adding or changing pages
To add additional pages create a new .html file in the website/templates/ folder.
The pages are made using jinja2 to template the basic layout and design of the webpages.
By including: {% extends "base.html" %} at the top of the file the new webpage will follow the template of the website
Please note to update the nav bar 2 files need to be changed: base.html & new_map.html
As due to time constraints I was unable to include the template of base.html in new_map.html.

## Remarks
Security check still need to be done before a production version can be launched.
The current version contains code to set up authentication, yet it is not implemented. Use with caution.

## Known bugs
In the web form if the user does not include a marker in every drawn polygon the data will not show in the portal.
