import re

from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from popyka.config import PopykaConfig
from popyka.core import Server


def test_postgresql_version_used_by_server_with_default_config():
    server = Server(config=PopykaConfig.get_default_config())
    cx: Connection = server.get_connection()
    with cx.cursor() as cur:
        cur: ReplicationCursor
        cur.execute("SELECT version()")
        results = cur.fetchall()
        match = re.fullmatch(r"^PostgreSQL\s+(\d+)\..+", results[0][0])
        assert match

        major_version = match.group(1)
        assert major_version == "16"


def test_postgresql_version_used_by_fixture(conn: Connection):
    with conn.cursor() as cur:
        cur: ReplicationCursor
        cur.execute("SELECT version()")
        results = cur.fetchall()
        match = re.fullmatch(r"^PostgreSQL\s+(\d+)\..+", results[0][0])
        assert match

        major_version = match.group(1)
        assert major_version == "16"
