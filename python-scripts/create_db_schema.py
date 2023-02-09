import psycopg2
from sqlalchemy import create_engine
import handy_defs as hd


res_folder_path = "./add-files"
config_file_name = "db_config.json"


def open_connection(config: dict):
    relevant_keys = {
        "host",
        "database",
        "port"
    }

    args = {
        "user": input('please enter db username: '), 
        "password": input('please enter db password: '), 
        **hd.select_keys(config, relevant_keys)
    }

    connection = psycopg2.connect(**args)
    return connection


def create_tables(connection, schema):
    with connection.cursor() as cursor:
        for table in schema:
            columns_str_list = [
                f'{col["name"]} {col["data_type"]} PRIMARY KEY' if "prim_key" in col
                else f'{col["name"]} {col["data_type"]}'
                for col in table["columns"]]
            columns_str_list = ','.join(columns_str_list)
            
            sql_str = f'CREATE TABLE {table["name"]} ({columns_str_list})'
            print(f'to db: {sql_str}')

            cursor.execute(sql_str)

        connection.commit()


def load_data_into_tables(data_df, table_name):

    engine = create_engine('postgresql://postgres:kaka@localhost:5432/streets_leipzig')
    data_df.to_sql(table_name, engine, schema= "public", index=False, if_exists='append')



if __name__ == "__main__":
    print('Start...')

    config_path = f'{res_folder_path}/{config_file_name}'
    config = hd.load_json(config_path)

    schema_path = f'{res_folder_path}/{config["schema"]}'
    schema = hd.load_json(schema_path)

    with open_connection(config) as conn:
        create_tables(conn, schema)

    print('Done')
