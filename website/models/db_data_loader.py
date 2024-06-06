#!/usr/bin/python
# By: Sander V
# Imports
import json
import os

from extensions import db
import psycopg2
from psycopg2.extras import RealDictCursor


# Functions
def load_db_data():
    """

    :return:
    """

    connect = psycopg2.connect(os.environ.get('SQLALCHEMY_DATABASE_URI'))
    print('Database connection established')
    cursor = connect.cursor(cursor_factory=RealDictCursor)

    # cur = db.Query(Catalog)
    cursor.execute('SELECT title, description, email, keywords, contact_person, '
                   'data_location, st_collectionextract(polygon_location,1'
                   ') AS points, st_collectionextract(polygon_location,3'
                   ') AS polygon FROM "CatalogMeta"')
    data_temp = cursor.fetchall()
    # standard method
    # Grab the data from the database
    # db_data = db.session.query(Catalog).all()
    # Create holding list
    list_o_dicts =[]
    # for each data entry in the database add dict to list
    # for data in db_data:
    #    list_o_dicts.append(data.to_dict())
    # dict_datasets = {item['dataset_id']:item for item in list_o_dicts}
    # create json of the list of dicts IF date object can be adjusted
    # datasets_json = json.dumps(list_o_dicts, indent=4, sort_keys=True, default=str)

    return data_temp

