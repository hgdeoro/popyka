import os

from popyka.config import PopykaConfig


def test_connect_url_default_value():
    default_config = PopykaConfig.get_default_config()
    assert default_config.database.connect_url == "postgresql://postgres:pass@localhost:54016/popyka_test"


def test_connect_url_overridden_value(monkeypatch):
    monkeypatch.setenv("POPYKA_DB_DSN", "this-value-was-overridden")
    default_config = PopykaConfig.get_default_config(environment=os.environ)
    assert default_config.database.connect_url == "this-value-was-overridden"
