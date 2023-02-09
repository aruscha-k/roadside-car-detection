import json

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


def select_keys(d: dict, keys) -> dict:
    return {k:v for k,v in d.items() if k in keys}