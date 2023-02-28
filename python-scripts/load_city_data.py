'''
script for loading city data into cut db
'''


import pandas as pd
import handy_defs as hd
from sqlalchemy import create_engine

config_path = "./add-files/db_config.json"

segments_path = './add-files/strassen_segmente_testgebiet.json'
segments_mapping_path = './add-files/strassen_segmente_testgebiet_mapping.json'


def coordinates_to_json(coordinates: list) -> str:
    return str(coordinates)


def extract_segment_data(segments_json, segments_mapping_json):
    global TRANSFORMATIONS

    tables = [map['postgres']['table'] for map in segments_mapping_json]
    keys = [map['postgres']['column'] for map in segments_mapping_json]
    columns = [
        [obj[map['city_data']['prop_level_1']][map['city_data']['prop_level_2']] for obj in segments_json['features']]
        for map in segments_mapping_json
    ]
    # column transformations
    columns = [
        [TRANSFORMATIONS[map['transformation']](x) for x in col] if 'transformation' in map else col
        for map, col in zip(segments_mapping_json, columns)
    ]

    tables_dict = hd.group_by(zip(tables, keys, columns), lambda x: x[0], lambda x: x[1:])
    print([(k, [(t[0], len(t[1]))for t in v]) for k,v in tables_dict.items()])

    return {k: pd.DataFrame(dict(v)) for k,v in tables_dict.items()}


def drop_duplicates(tables_dict, tables_primary_keys):
    result = dict()
    for item in tables_primary_keys:
        tab, prim_key = item['table'], item['key']
        result[tab] = tables_dict[tab].drop_duplicates(subset=[prim_key])

    print([(k, len(v)) for k,v in result.items()])

    return result

def write_tables_to_db(tables_dict, transmission_order, config):
    username = input('please enter db username: ')
    password = input('please enter db password: ')
    engine = create_engine(f'postgresql://{username}:{password}@{config["host"]}:{config["port"]}/{config["database"]}')

    for table in transmission_order:
        tables_dict[table].to_sql(table, engine, index=False, if_exists='append')


TRANSFORMATIONS = {
    "coordinates_to_json": coordinates_to_json
}


if __name__ == "__main__":
    print('Start...')

    config = hd.load_json(config_path)

    segments_json = hd.load_json(segments_path, 'rb')
    segments_mapping_json = hd.load_json(segments_mapping_path)

    tables_dict = extract_segment_data(segments_json, segments_mapping_json['mapping'])
    tables_dict_no_dup = drop_duplicates(tables_dict, segments_mapping_json['tables_primary_keys'])
    write_tables_to_db(tables_dict_no_dup, segments_mapping_json['transmission_order'], config)

    print('Done')