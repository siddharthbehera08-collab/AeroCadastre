import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def main():
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    db_pwd = os.getenv("DB_PASSWORD", "aerocadastre_dev")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname='aerocadastre'")
    if not cur.fetchone():
        cur.execute("CREATE ROLE aerocadastre WITH LOGIN SUPERUSER PASSWORD %s;", (db_pwd,))
        print("Created role aerocadastre")
    else:
        print("Role aerocadastre already exists")

    cur.execute("SELECT 1 FROM pg_database WHERE datname='aerocadastre'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE aerocadastre OWNER aerocadastre;")
        print("Created database aerocadastre")
    else:
        print("Database aerocadastre already exists")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
