import pathlib

import yaml

from popyka.config import PopykaConfig


def test_default_config_instantiate(popyka_env_vars):
    default_config_file = pathlib.Path(__file__).parent.parent / "popyka" / "popyka-default.yaml"
    parsed_config = yaml.safe_load(default_config_file.read_text())
    config = PopykaConfig.from_dict(parsed_config, environment=popyka_env_vars)

    for filter_config in config.filters:
        filter_config.instantiate()

    for processor_config in config.processors:
        processor_config.instantiate()
