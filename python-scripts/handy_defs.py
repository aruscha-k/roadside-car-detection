import json
import psycopg2

def load_json(path: str, mode: str=None):
    data = None
    if mode is not None:
        with open(path, mode) as f:
            data = json.load(f)
    else:
        with open(path) as f:
            data = json.load(f)

    if data is None:
        raise ValueError(f'cant import file by path "{path}"')
    return data

def open_connection(config: dict):
    relevant_keys = {
        "host",
        "database",
        "port"
    }

    args = {
        "user": input('please enter db username: '), 
        "password": input('please enter db password: '), 
        **select_keys(config, relevant_keys)
    }

    connection = psycopg2.connect(**args)
    return connection

def select_keys(d: dict, keys) -> dict:
    return {k:v for k,v in d.items() if k in keys}

def group_by(iterable, get_key, get_value=None) -> dict:
    result = dict()
    for item in iterable:
        key = get_key(item)
        value = get_value(item) if get_value is not None else item

        if key not in result:
            result[key] = []
        result[key].append(value)

    return result