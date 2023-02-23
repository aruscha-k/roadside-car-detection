'''
script vor db creation as given in schema config
'''

import handy_defs as hd


res_folder_path = "./add-files"
config_file_name = "db_config.json"


def schema_to_sql(schema: dict) -> list[str]:
    sql_list = []

    tab_prim_key_dict = {tab['name']: [col['name'] for col in tab['columns'] if 'primary key' in col] for tab in schema}
    tab_prim_key_dict = {k:v[0] for k,v in tab_prim_key_dict.items() if any(v)}

    for table in schema:
        non_attributes = ['name', 'type', 'references']
        col_names = [col['name'] for col in table["columns"]]
        col_datatypes = [col['type'] for col in table["columns"]]
        col_attributes = [[k for k in col if k not in non_attributes] for col in table["columns"]]
        col_attributes = [' '.join(a) if any(a) else None for a in col_attributes]
        col_references = [f'references {col["references"]}({tab_prim_key_dict[col["references"]]})' if 'references' in col else None for col in table["columns"]]
        
        column_str_list = [' '.join([x for x in t if x is not None]) for t in zip(col_names, col_datatypes, col_attributes, col_references)]
        column_str_list = [f'\t{col}' for col in column_str_list]
        columns_str = ',\n'.join(column_str_list)
        
        sql_str = f'CREATE TABLE {table["name"]} (\n{columns_str})'
        sql_list.append(sql_str)
    
    return sql_list

def create_tables(connection, sql_list: list[str]):
    with connection.cursor() as cursor:
        for sql_str in sql_list:
            print(f'to db: {sql_str}')
            cursor.execute(sql_str)
        connection.commit()


if __name__ == "__main__":
    print('Start...')

    config_path = f'{res_folder_path}/{config_file_name}'
    config = hd.load_json(config_path)

    schema_path = f'{res_folder_path}/{config["schema"]}'
    schema = hd.load_json(schema_path)

    sql_list = schema_to_sql(schema)

    with hd.open_connection(config) as con:
        create_tables(con, sql_list)

    print('Done')
