import psycopg2


def test_schema_and_postgis():
    conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre")
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Total tables created ({len(tables)}):")
    for t in tables:
        print(" -", t)

    print("\nTesting PostGIS spatial functions:")
    cur.execute("SELECT ST_IsValid(ST_GeomFromText('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))', 4326));")
    print("ST_IsValid:          ", cur.fetchone()[0])

    cur.execute("SELECT ST_Area(ST_GeomFromText('POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))', 32643));")
    print("ST_Area (sqm):       ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_Intersects(ST_GeomFromText('POLYGON((0 0, 0 2, 2 2, 2 0, 0 0))', 4326), ST_GeomFromText('POLYGON((1 1, 1 3, 3 3, 3 1, 1 1))', 4326));"
    )
    print("ST_Intersects:       ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_Contains(ST_GeomFromText('POLYGON((0 0, 0 5, 5 5, 5 0, 0 0))', 4326), ST_GeomFromText('POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))', 4326));"
    )
    print("ST_Contains:         ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_Within(ST_GeomFromText('POINT(2 2)', 4326), ST_GeomFromText('POLYGON((0 0, 0 5, 5 5, 5 0, 0 0))', 4326));"
    )
    print("ST_Within:           ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_Overlaps(ST_GeomFromText('POLYGON((0 0, 0 2, 2 2, 2 0, 0 0))', 4326), ST_GeomFromText('POLYGON((1 0, 1 2, 3 2, 3 0, 1 0))', 4326));"
    )
    print("ST_Overlaps:         ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_Distance(ST_GeomFromText('POINT(0 0)', 32643), ST_GeomFromText('POINT(30 40)', 32643));"
    )
    print("ST_Distance:         ", cur.fetchone()[0])

    cur.execute(
        "SELECT ST_AsText(ST_MakeValid(ST_GeomFromText('POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))', 4326)));"
    )
    print("ST_MakeValid:        ", cur.fetchone()[0])

    cur.close()
    conn.close()


if __name__ == "__main__":
    test_schema_and_postgis()
