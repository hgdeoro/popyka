import copy
import pathlib

import pytest
import yaml
from pydantic import ValidationError

from popyka.config import PopykaConfig
from popyka.errors import ConfigError


class TestDefaultConfig:
    def test_default_config_with_fixture(self, popyka_env_vars):
        # Default config is expected to WORK when the fixture `popyka_env_vars` is used
        default_config = PopykaConfig.get_config(environment=popyka_env_vars)
        assert default_config

    def test_default_config_without_fixture(self):
        # Default config is expected to FAIL without `popyka_env_vars`
        with pytest.raises(ConfigError):
            PopykaConfig.get_config(environment={})

    def test_default_config_instantiate(self, popyka_env_vars):
        default_config_file = pathlib.Path(__file__).parent.parent.parent / "popyka" / "popyka-default.yaml"
        parsed_config = yaml.safe_load(default_config_file.read_text())
        config = PopykaConfig.from_dict(parsed_config, environment=popyka_env_vars)

        for filter_config in config.filters:
            filter_config.instantiate()

        for processor_config in config.processors:
            processor_config.instantiate()


@pytest.fixture
def min_config() -> dict:
    """Most basic an minimal valid configuration"""
    return copy.deepcopy(
        {
            "database": {
                "connect_url": "some-text",
                "slot_name": "some-text",
            },
            "filters": [],
            "processors": [
                {
                    "class": "some-text",
                }
            ],
        }
    )


class TestMinConfig:
    def test_min_config_works(self, min_config: dict):
        assert PopykaConfig.from_dict(min_config)

    def test_fails_without_connect_url(self, min_config: dict):
        del min_config["database"]["connect_url"]
        with pytest.raises(ValidationError):
            PopykaConfig.from_dict(min_config)

    def test_fails_without_slot_name(self, min_config: dict):
        del min_config["database"]["slot_name"]
        with pytest.raises(ValidationError):
            PopykaConfig.from_dict(min_config)

    def test_fails_without_filters(self, min_config: dict):
        del min_config["filters"]
        with pytest.raises(ValidationError):
            PopykaConfig.from_dict(min_config)

    def test_fails_without_processors(self, min_config: dict):
        del min_config["processors"]
        with pytest.raises(ValidationError):
            PopykaConfig.from_dict(min_config)


class TestConfigFilter:
    def test_empty_filter(self, min_config):
        assert not min_config["filters"]
        min_config["filters"].append({})
        with pytest.raises(ValidationError):
            PopykaConfig.from_dict(min_config)

    def test_filter_with_class(self, min_config):
        assert not min_config["filters"]
        min_config["filters"].append({"class": "some-text"})
        assert PopykaConfig.from_dict(min_config)

    def test_filter_with_class_and_config(self, min_config):
        assert not min_config["filters"]
        min_config["filters"].append({"class": "some-text", "config": {}})
        assert PopykaConfig.from_dict(min_config)


class TestCustomConfig:
    def test_default_when_config_file_env_is_empty_string(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = ""
        default_config = PopykaConfig.get_config(environment=popyka_env_vars)
        assert default_config

    def test_default_when_config_file_env_string_is_space_only(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = "  "
        default_config = PopykaConfig.get_config(environment=popyka_env_vars)
        assert default_config

    def test_fails_file_does_not_exists(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = "/this/path/does/not/exists.yaml"
        with pytest.raises(ConfigError, match="Invalid config:.*POPYKA_CONFIG.*does not exists"):
            PopykaConfig.get_config(environment=popyka_env_vars)

    def test_fails_with_directory(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = "/"
        with pytest.raises(ConfigError, match="Invalid config:.*POPYKA_CONFIG.*is a directory"):
            PopykaConfig.get_config(environment=popyka_env_vars)

    def test_load_alternative(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = str(
            pathlib.Path(__file__).parent.parent / "resources" / "config-alternative.yaml"
        )
        config = PopykaConfig.get_config(environment=popyka_env_vars)

        assert config.database.connect_url == "config-alternative"
        assert config.database.slot_name == "config-alternative"
