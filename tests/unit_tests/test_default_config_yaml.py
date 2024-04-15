import pathlib

import pytest
import yaml

from popyka.config import PopykaConfig
from popyka.errors import ConfigError


def test_default_config_with_fixture(popyka_env_vars):
    # Default config is expected to WORK when the fixture `popyka_env_vars` is used
    default_config = PopykaConfig.get_default_config(environment=popyka_env_vars)
    assert default_config


def test_default_config_without_fixture():
    # Default config is expected to FAIL without `popyka_env_vars`
    with pytest.raises(ConfigError):
        PopykaConfig.get_default_config(environment={})


def test_default_config_instantiate(popyka_env_vars):
    default_config_file = pathlib.Path(__file__).parent.parent.parent / "popyka" / "popyka-default.yaml"
    parsed_config = yaml.safe_load(default_config_file.read_text())
    config = PopykaConfig.from_dict(parsed_config, environment=popyka_env_vars)

    for filter_config in config.filters:
        filter_config.instantiate()

    for processor_config in config.processors:
        processor_config.instantiate()
