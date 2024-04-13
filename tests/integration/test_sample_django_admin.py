import http.client
import pathlib

import pytest


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    dc_file = pathlib.Path(__file__).parent.parent.parent / "samples" / "django-admin" / "docker-compose.yml"
    return dc_file.absolute()


@pytest.fixture(scope="session")
def docker_compose_project_name(pytestconfig):
    return "django-admin"


def is_up(host, path):
    conn = http.client.HTTPConnection(host)
    conn.request("GET", path)
    r1 = conn.getresponse()
    print(r1.status, r1.reason)
    return r1.status == 200


@pytest.fixture(scope="session")
def django_admin_service(docker_ip, docker_services):
    """Ensure that HTTP service is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("demo-django-admin", 8080)
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_up(f"{docker_ip}:{port}", "/"))
    return docker_ip, port


def test_status_code(django_admin_service):
    docker_ip, port = django_admin_service

    conn = http.client.HTTPConnection(f"{docker_ip}:{port}")
    conn.request("GET", "/admin/")
    r1 = conn.getresponse()
    print(r1.status, r1.reason)
    assert r1.status == 200
