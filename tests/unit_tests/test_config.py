import pathlib

import pytest
import yaml

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


class TestCustomConfig:
    def test_fails_file_does_not_exists(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = "/this/path/does/not/exists.yaml"
        with pytest.raises(ConfigError, match="Invalid config:.*POPYKA_CONFIG.*does not exists"):
            PopykaConfig.get_config(environment=popyka_env_vars)

    def test_fails_with_directory(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = "/"
        with pytest.raises(ConfigError, match="Invalid config:.*POPYKA_CONFIG.*is a directory"):
            PopykaConfig.get_config(environment=popyka_env_vars)

    def test_load_alternative(self, popyka_env_vars):
        popyka_env_vars["POPYKA_CONFIG"] = (
            pathlib.Path(__file__).parent.parent / "resources" / "config-alternative.yaml"
        )
        config = PopykaConfig.get_config(environment=popyka_env_vars)

        assert config.database.connect_url == "config-alternative"
        assert config.database.slot_name == "config-alternative"
