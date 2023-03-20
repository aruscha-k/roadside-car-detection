'''
script for loading city data into cut db
'''

import pandas as pd
import DB_helpers as db_helper
from sqlalchemy import create_engine
from PATH_CONFIGS import LOAD_DATA_CONFIG_NAME, RES_FOLDER_PATH, DATASET_FOLDER_PATH




def coordinates_to_json(coordinates: list) -> str:
    return str(coordinates)
TRANSFORMATIONS = {
    "coordinates_to_json": coordinates_to_json
}


def extract_data(data_json, path_to_data_set, mapping_json):
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
    engine = create_engine(f'postgresql://{username}:{password}@{config["host"]}:{config["port"]}/{config["database"]}')
    for table in transmission_order:
        dfs_dict[table].to_sql(table, engine, index=False, if_exists='append')

def load_data(data_sets, mappings, db_config) -> None:
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
def main(res_folder_path:str=None, load_data_config_name:str=None, data_set_path:str=None) -> None:
    global RES_FOLDER_PATH, LOAD_DATA_CONFIG_NAME, DATASET_FOLDER_PATH
    
    print('Start load_data...')

    if not res_folder_path:
        res_folder_path = RES_FOLDER_PATH
    if not load_data_config_name:
        load_data_config_name = LOAD_DATA_CONFIG_NAME
    if not data_set_path:
        data_set_path = DATASET_FOLDER_PATH

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
    main()