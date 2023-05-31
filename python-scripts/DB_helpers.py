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


def open_connection(db_config_path: str, db_user_config_path:str):
    relevant_keys = {
        "host",
        "database",
        "port"
    }
    config = load_json(db_config_path)
    user_config = load_json(db_user_config_path)
    user = user_config['username']
    pw = user_config['password']

    args = {
        "user": user, 
        "password": pw, 
        **select_keys(config, relevant_keys)
    }

    connection = psycopg2.connect(**args)
    return connection


def select_keys(d: dict, keys) -> dict:
    """
    The select_keys function is designed to return a new dictionary that contains only the key-value pairs from the original dictionary (d) where the key is present in the given list keys.
    Parameters:
        d (dict): the dictionary from which to select key-value pairs
        keys (list): a list of keys to select from the dictionary
    Returns:
        dict: a new dictionary containing only the selected key-value pairs"""
    return {k:v for k,v in d.items() if k in keys}


def navigate_json_dict(json_dict, json_path:list):
    """
    The navigate_json_dict function is designed to retrieve a nested value from a JSON dictionary using a path of keys.
    Parameters:
        json_dict (dict): the JSON dictionary to navigate
        json_path (list): a list of keys representing the path to the desired value
    Returns:
        result_item (any): the value located at the end of the path"""

    result_item = json_dict
    for property in json_path:
        try:
            result_item = result_item[property]
        except KeyError:
            return None
    return result_item


def group_by(iterable, get_key, get_value=None) -> dict:
    """
    The group_by function is designed to group items from an iterable based on a key extracted from each item.
    Parameters:
        iterable (iterable): the iterable to group items from
        get_key (callable): a function that extracts the key from each item
        get_value (callable, optional): a function that extracts the value from each item. If not provided, the entire item will be used as the value.
    Returns:
        result (dict): a dictionary where each key corresponds to a group of items that share the same key"""
    result = dict()
    for item in iterable:
        key = get_key(item)
        value = get_value(item) if get_value is not None else item

        if key not in result:
            result[key] = []
        result[key].append(value)

    return result