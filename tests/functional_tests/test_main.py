import logging
import pathlib
import uuid

from tests.utils.db_activity_simulator import DbActivitySimulator
from tests.utils.subp_collector import SubProcCollector

logger = logging.getLogger(__name__)


def test_main(
    dsn: str, conn, drop_slot, table_name: str, popyka_env_vars, monkeypatch, subp_coll: type[SubProcCollector]
):
    config_file = pathlib.Path(__file__).parent.parent / "resources" / "config-test-main.yaml"
    popyka_env_vars["POPYKA_CONFIG"] = str(config_file.absolute())
    popyka_env_vars["LAZYTOSTR_COMPACT"] = "1"

    for key, value in popyka_env_vars.items():
        monkeypatch.setenv(key, value)

    args = ["python3", "-m", "popyka"]
    main = subp_coll(args=args)

    main.start()
    main.wait_for("Using custom config file")
    main.wait_for("will consume_stream() adaptor=")

    uuids = [str(uuid.uuid4()) for _ in range(4)]
    statements = [("INSERT INTO {table_name} (NAME) VALUES (%s)", [_]) for _ in uuids]
    db_activity_simulator = DbActivitySimulator(conn, table_name, statements)
    db_activity_simulator.start()
    db_activity_simulator.join_or_fail(timeout=2)

    changes = []
    for an_uuid in uuids:
        change = main.wait_for_change(timeout=3)
        changes.append(change)
        assert change["action"] == "I"
        assert change["columns"][0]["value"] == an_uuid

    main.kill()
    main.wait()
    main.join_threads()

    assert len(changes) == 4
