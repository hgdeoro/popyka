import os
import re

from psycopg2.extensions import connection as Connection
from psycopg2.extras import ReplicationCursor

from popyka.config import PopykaConfig
from popyka.server import Server

EXPECTED_POSTGRESQL_MAJOR_VERSION = os.environ.get("EXPECTED_POSTGRESQL_MAJOR_VERSION", "16")


def test_postgresql_version_used_by_server_with_default_config(popyka_env_vars):
    server = Server(config=PopykaConfig.get_config(environment=popyka_env_vars))
    cx: Connection = server.get_connection()
    with cx.cursor() as cur:
        cur: ReplicationCursor
        cur.execute("SELECT version()")
        results = cur.fetchall()
        match = re.fullmatch(r"^PostgreSQL\s+(\d+)\..+", results[0][0])
        assert match

        real_major_version = match.group(1)
        assert real_major_version == EXPECTED_POSTGRESQL_MAJOR_VERSION


def test_postgresql_version_used_by_fixture(conn: Connection):
    with conn.cursor() as cur:
        cur: ReplicationCursor
        cur.execute("SELECT version()")
        results = cur.fetchall()
        match = re.fullmatch(r"^PostgreSQL\s+(\d+)\..+", results[0][0])
        assert match

        real_major_version = match.group(1)
        assert real_major_version == EXPECTED_POSTGRESQL_MAJOR_VERSION
