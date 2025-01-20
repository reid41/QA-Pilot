import psycopg2
import configparser

config = configparser.ConfigParser()
config.read('config/config.ini')
db_config = config['database']

try:
    conn = psycopg2.connect(
        dbname=db_config['db_name'],
        user=db_config['db_user'],
        password=db_config['db_password'],
        host=db_config['db_host'],
        port=db_config['db_port']
    )
    print("Connection successful")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print(f"Database version: {db_version}")
    cur.close()
    conn.close()
except psycopg2.Error as e:
    print(f"Error: {e}")