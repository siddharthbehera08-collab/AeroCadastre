import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def main() -> None:
    conn = psycopg2.connect("dbname=postgres user=postgres host=127.0.0.1 port=5432")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'aerocadastre'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE aerocadastre")
        print("Created database: aerocadastre")
    else:
        print("Database aerocadastre already exists")
    cur.close()
    conn.close()

    conn2 = psycopg2.connect("dbname=aerocadastre user=postgres host=127.0.0.1 port=5432")
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur2 = conn2.cursor()
    cur2.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    cur2.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
    cur2.execute("SELECT version(), PostGIS_Full_Version();")
    pg_ver, postgis_ver = cur2.fetchone()
    print("PostgreSQL Version:", pg_ver)
    print("PostGIS Version:   ", postgis_ver)
    cur2.close()
    conn2.close()


if __name__ == "__main__":
    main()
