import psycopg2


def test_connect_to_template1():
    conn = psycopg2.connect("host=localhost port=5432 dbname=template1 user=postgres")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    records = cur.fetchall()
    assert records == [(1, )]
