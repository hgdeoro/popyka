import pathlib
import random

import mechanize
import pytest

from tests.conftest import system_test
from tests.subp_collector import SubProcCollector

# https://github.com/avast/pytest-docker


@pytest.fixture
def dc_deps() -> SubProcCollector:
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--build",
        "--wait",
        "-d",
        "demo-db",
        "demo-django-admin",
        "demo-kafka",
    ]
    subp_collector = SubProcCollector(args=args).start()
    assert subp_collector._proc.wait() == 0  # Retry? Timeout?  # FIXME: protected attribute!
    subp_collector._thread_stdout.join()  # FIXME: protected attribute!
    subp_collector._thread_stderr.join()  # FIXME: protected attribute!

    yield subp_collector


@pytest.fixture
def dc_popyka(monkeypatch) -> SubProcCollector:
    slot_name = f"django_admin_demo_popyka_{random.randint(1, 999999999)}"
    monkeypatch.setenv("POPYKA_DB_SLOT_NAME", slot_name)

    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    args = [
        "docker",
        "compose",
        "--file",
        str(dc_file.absolute()),
        "up",
        "--build",
        "demo-popyka",
    ]
    subp_collector = SubProcCollector(args=args).start()

    # Wait until Popyka started
    subp_collector.wait_for(f"will start_replication() slot={slot_name}", timeout=5)
    subp_collector.wait_for("will consume_stream() adaptor=", timeout=1)

    yield subp_collector

    subp_collector.kill()
    subp_collector._proc.wait()  # FIXME: protected attribute!
    subp_collector._thread_stdout.join()  # FIXME: protected attribute!
    subp_collector._thread_stderr.join()  # FIXME: protected attribute!


@system_test
def test_default_configuration(dc_deps: SubProcCollector, dc_popyka: SubProcCollector):
    docker_ip, port = "localhost", "8081"
    br = mechanize.Browser()
    br.set_handle_robots(False)

    br.open(f"http://{docker_ip}:{port}/admin/")
    assert br.response().code == 200
    assert br.title() == "Log in | Django site admin"

    br.select_form(nr=0)
    br["username"] = "admin"
    br["password"] = "admin"
    br.submit()

    assert br.response().code == 200
    assert br.title() == "Site administration | Django site admin"

    dc_popyka.wait_for('"table": "django_session"', timeout=5)
    dc_popyka.wait_for('"table": "auth_user"', timeout=5)
