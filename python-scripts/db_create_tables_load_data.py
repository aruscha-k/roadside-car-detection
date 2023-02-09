import psycopg2
from sqlalchemy import create_engine


def open_connection():
    connection = psycopg2.connect(
            host = "localhost",
            database = "streets_leipzig",
            port = 5432)
    return connection


def create_street_tables(connection):
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE streets (
	        street_nr int PRIMARY KEY,
            street_name text)
        """)

    connection.commit()


def load_data_into_tables(data_df, table_name):

    engine = create_engine('postgresql://postgres:kaka@localhost:5432/streets_leipzig')
    data_df.to_sql(table_name, engine, schema= "public", index=False, if_exists='append')



if __name__ == "__main__":

    conn = open_connection()
    create_street_tables(conn)