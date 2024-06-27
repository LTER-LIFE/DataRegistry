#!/usr/bin/python
# By: Sander V
# Imports
import json
import os
import pandas as pd
from extensions import db
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
import geopandas as gpd

# Functions
def load_db_data():
    """

    :return:
    """

    connect = psycopg2.connect(os.environ.get('SQLALCHEMY_DATABASE_URI'))
    print('Database connection established')
    # cursor = connect.cursor()
    # cursor = connect.cursor(cursor_factory=RealDictCursor)
    #
    #
    # # cur = db.Query(Catalog)
    # cursor.execute('SELECT id,title, st_asgeojson(st_collectionextract('
    #                'polygon_location,1)) AS markers ,'
    #                'description, email, keywords, '
    #                'contact_person, '
    #                'data_location, (ST_Y(ST_AsText(ST_GeometryN(st_collectionextract('
    #                'polygon_location,1'
    #                '),1))),'
    #                'ST_X(ST_AsText(ST_GeometryN(st_collectionextract('
    #                'polygon_location,1'
    #                '),1)))) AS points, ST_AsGeoJSON(st_collectionextract('
    #                'polygon_location,3'
    #                ')) AS polygon, collect_year_start, collect_year_end FROM "CatalogMeta"')
    # data_temp = cursor.fetchall()
    # cursor.close()
    cursor = connect.cursor()
    cursor.execute('''SELECT st_asgeojson("CatalogMeta") FROM "CatalogMeta"''')
    data_json = [json.loads(i[0]) for i in cursor.fetchall()]



    cursor.close()


    # standard method
    # Grab the data from the database and turn it into a dict
    # dict_datasets = {item['id']:item for item in data_temp}


    return data_json


def load_db_table():
    '''

    :return:
    '''
    connect = psycopg2.connect(os.environ.get('SQLALCHEMY_DATABASE_URI'))
    print('Database connection established')

    cursor = connect.cursor()

    datasets_table = pd.read_sql_query('''SELECT title, email, keywords, 
    contact_person, collect_year_start, collect_year_end, data_location FROM 
    "CatalogMeta"''', connect)
    cursor.close()
    return datasets_table
