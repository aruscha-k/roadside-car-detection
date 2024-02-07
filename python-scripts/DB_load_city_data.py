'''
script for loading city data into cut db
'''

import json
import pandas as pd
import DB_helpers as db_helper
import psycopg2
from sqlalchemy import create_engine

from PATH_CONFIGS import LOAD_DATA_CONFIG_NAME, RES_FOLDER_PATH, DATASET_FOLDER_PATH, DB_CONFIG_FILE_NAME


def coordinates_to_json(coordinates: list) -> str:
    return str(coordinates)

def geom_to_json(geometry: dict):
    return json.dumps(geometry)


TRANSFORMATIONS = {
    "coordinates_to_json": coordinates_to_json,
    "geom_to_json": geom_to_json
}


def extract_data(data_json, path_to_data_set, mapping_json):
    """
    The extract_data function is designed to extract data from a JSON object and transform it into a dictionary of Pandas dataframes.
    Parameters:
        data_json (dict): the JSON object to extract data from
        path_to_data_set (list): a list of keys representing the path to the data set within the JSON object
        mapping_json (list): a list of dictionaries that define the mapping between JSON properties and PostgreSQL columns. Each dictionary should have the keys 'path_to_property' (a list of keys representing the path to the JSON property), 'postgres.table' (the name of the PostgreSQL table), and 'postgres.column' (the name of the PostgreSQL column).
    Returns:
        dict: a dictionary where the keys are the names of the PostgreSQL tables and the values are Pandas dataframes containing the extracted data.
    """
    global TRANSFORMATIONS

    tables = [map['postgres']['table'] for map in mapping_json]
    keys = [map['postgres']['column'] for map in mapping_json]
    columns = [
        [db_helper.navigate_json_dict(obj, map['path_to_property']) for obj in db_helper.navigate_json_dict(data_json, path_to_data_set)]
        for map in mapping_json
    ]
    # column transformations
    columns = [
        [TRANSFORMATIONS[map['transformation']](x) for x in col] if 'transformation' in map else col
        for map, col in zip(mapping_json, columns)
    ]

    tables_dict = db_helper.group_by(zip(tables, keys, columns), lambda x: x[0], lambda x: x[1:])
    print('extracted tables <table, [(column_name, item_count)]>')
    for k,v in tables_dict.items():
        print(k, [(t[0], len(t[1]))for t in v])
    print('')

    return {k: pd.DataFrame(dict(v)) for k,v in tables_dict.items()}


def drop_duplicates(df_dict, tables_primary_keys):
    """
    The drop_duplicates function is designed to remove duplicate rows from Pandas dataframes in a dictionary.
    Parameters:
        df_dict (dict): a dictionary where the keys are the names of the tables and the values are Pandas dataframes
        tables_primary_keys (list): a list of dictionaries that define the primary keys for each table. Each dictionary should have the keys 'table' (the name of the table) and 'key' (the name of the primary key column).
    Returns:
        dict: a dictionary where the keys are the names of the tables and the values are Pandas dataframes with duplicate rows removed based on the specified primary keys.
    """
    result = dict()
    for item in tables_primary_keys:
        tab, prim_key = item['table'], item['key']
        result[tab] = df_dict[tab].drop_duplicates(subset=[prim_key])

    print('tables after drop_duplicates <table, item_count>')
    for k,v in result.items():
        print(k, len(v))
    print('')

    return result


def write_dfs_to_db(dfs_dict, transmission_order, config, username, password):
    """
    The write_dfs_to_db function is designed to write Pandas dataframes in a dictionary to a PostgreSQL database.
    Parameters:
        dfs_dict (dict): a dictionary where the keys are the names of the tables and the values are Pandas dataframes
        transmission_order (list): a list of strings that define the order in which the tables should be written to the database
        config (dict): a dictionary that contains the database configuration details, including the host, port, and database name
        username (str): the username to connect to the database
        password (str): the password to connect to the database
    """
    engine = create_engine(f'postgresql://{username}:{password}@{config["host"]}:{config["port"]}/{config["database"]}')
    for table in transmission_order:
        dfs_dict[table].to_sql(table, engine, index=False, if_exists='append')


def load_data(data_sets, mappings, db_config) -> None:
    """
    The load_data function takes in three parameters, data_sets, mappings, and db_config. It extracts data from the given data sets using the provided mappings, removes duplicates from the extracted data, and sends the resulting data to a database using the provided database configuration.
    Parameters:
        data_sets (list): A list of data sets.
        mappings (list): A list of dictionaries where each dictionary contains the following keys:
            mapping (dict): A dictionary containing mapping details between columns of the data and the database.
            path_to_data_set (str): The path to the data set file.
            tables_primary_keys (list): A list of primary keys for the tables in the data set.
            transmission_order (list): A list of table names in the order in which they should be transmitted to the database.
        db_config (dict): A dictionary containing the following keys:
            database (str): The name of the database.
            host (str): The hostname of the database.
            port (int): The port number of the database.
            user (str): The username for the database.
            password (str): The password for the database.
    """
    mapping_list = [m['mapping'] for m in mappings]
    path_to_data_sets = [m['path_to_data_set'] for m in mappings]
    tables_primary_keys_list = [m['tables_primary_keys'] for m in mappings]
    transmission_order_list = [m['transmission_order'] for m in mappings]

    dfs_dicts = [extract_data(data, path, mapping) for data, path, mapping in zip(data_sets, path_to_data_sets, mapping_list)]
    dfs_dict_no_dups = [drop_duplicates(dfs_dict, tables_primary_keys) for dfs_dict, tables_primary_keys in zip(dfs_dicts, tables_primary_keys_list)]

    print('send data to db...')
    username = input('please enter db username: ')
    password = input('please enter db password: ')
    for dfs_dict, transmission_order in zip(dfs_dict_no_dups, transmission_order_list):
        write_dfs_to_db(dfs_dict, transmission_order, db_config, username, password)



# methodto call, if this file will be imported and run by another file.
# in this case res_folder_path and load_data_config_name can be set. otherwise the standart files will be used
def run_read_city_data(res_folder_path:str=None, load_data_config_name:str=None, data_set_path:str=None) -> None:
    global RES_FOLDER_PATH, LOAD_DATA_CONFIG_NAME, DATASET_FOLDER_PATH

    if not res_folder_path:
        res_folder_path = RES_FOLDER_PATH
    if not load_data_config_name:
        load_data_config_name = LOAD_DATA_CONFIG_NAME
    if not data_set_path:
        data_set_path = DATASET_FOLDER_PATH

    print('Start load_data...')

    load_data_config_path = f'{res_folder_path}/{load_data_config_name}'
    load_data_config = db_helper.load_json(load_data_config_path)

    db_config_path = f'{res_folder_path}/{load_data_config["db_config"]}'
    db_config = db_helper.load_json(db_config_path)

    data_sets_filenames = [item['file_path'] for item in load_data_config['data_scources']]
    mappings_filenames = [item['mapping_path'] for item in load_data_config['data_scources']]
    data_sets_paths = [f'{data_set_path}/{name}' for name in data_sets_filenames]
    mappings_paths = [f'{res_folder_path}/{name}' for name in mappings_filenames]

    data_sets = [db_helper.load_json(path, 'rb') for path in data_sets_paths]
    mappings = [db_helper.load_json(path, 'rb') for path in mappings_paths]

    load_data(data_sets, mappings, db_config)
    print('load_data Done')



if __name__ == "__main__":

#    run_read_city_data(RES_FOLDER_PATH, LOAD_DATA_CONFIG_NAME, DATASET_FOLDER_PATH)
    run_read_city_data()