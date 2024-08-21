# Notes on the folder structure
In the current version the most important folder is the website folder.
Other important files are the .env, app.py, config.py, extensions.py & the yaml for the dependencies. 

Alembic folder:
The alembic folder contains different versions of the database (if alembic is used to update the database)

#### website/models
Contains the various models of the application (including user models that are not implemented)
Of specific importance:
- db_data_loader.py 
    retrieves data from the database to display on the map
- models.py
    contains the model of the database/table (needs to match the databasetable)

#### website/resources
Only important if user accounts are going to be implemented

#### website/schemas
Only important if user accounts are going to be implemented

#### website/static
Contains the different stylesheets, images, CSS and JavaScript dependencies

#### website/templates
Contains the .html templates 
base.html is the jinja2 template that can be used to extend other webpages.
REMINDER: new_map.html does not make use of jinja2 template at the moment. Thus changes made to base.html do not
affect new_map.html (important for the nav bar).

#### website/forms.py
Contains the web form

#### website/routes.py
Old version (no longer in use but contains set up for future pages)

#### website/views.py
Contains the routes to all the individual webpages.

#### .env  AND OR .env_template
File to establish connection with the database (keep the values hidden) thats why the .env_template is empty.
***rename .env_template to .env***

#### extensions.py
Required file that manages the extensions of the application

#### config.py
Set up for the application, essentially takes the hidden values from .env and uses them.

#### app.py
Main script to run the application.
