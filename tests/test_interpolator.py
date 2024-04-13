import json
import pathlib
import uuid

import yaml

from popyka.interpolation import Interpolator

# FIXME: test with all yaml data types (int, bool, etc.)


def test_interpolator_without_env():
    original_config = {
        "key_1": "value_1",
        "key_2": "value_2",
        "dict_plain": {
            "key_1": "value_1",
            "key_2": "value_2",
        },
        "dict_complex": {
            "key_1": "value_1",
            "list_str": ["value_1", "value_2"],
            "list_dict_str": [
                {
                    "k1": "v1",
                    "k2": "v2",
                },
                {
                    "k3": "v3",
                    "k4": "v4",
                },
            ],
        },
    }
    interpolator = Interpolator(environment={})
    config = interpolator.interpolate(config=original_config)
    assert config is not original_config
    assert config == original_config


def test_interpolator_yaml_types():
    """
    --- supported types
    !!bool 	bool
    !!int 	int
    !!float 	float
    !!str     str
    !!seq     list
    !!map     dict
    !!null 	None

    --- NOT supported types
    !!binary 	str (bytes in Python 3)
    !!timestamp   datetime.datetime
    !!omap, !!pairs 	list of pairs
    !!set     set
    """

    interpolator = Interpolator(environment={})
    yaml_path = pathlib.Path(__file__).parent / "all_yaml_types.yaml"
    config_yaml = yaml.safe_load(yaml_path.read_text())
    assert config_yaml == {
        "string": "value",
        "integer": 123,
        "float": 3.14,
        "bool": True,
        "list": ["a", "b"],
        "dict": {"k1": "v1"},
        "null": None,
    }
    interpolator.interpolate(config=config_yaml)


def test_interpolator_with_env():
    environment: dict[str, str] = {
        "INTERPOLATION_A": str(uuid.uuid4()),
        "INTERPOLATION_B": str(uuid.uuid4()),
        "INTERPOLATION_C": str(uuid.uuid4()),
        "INTERPOLATION_D": str(uuid.uuid4()),
        "INTERPOLATION_E": str(uuid.uuid4()),
    }

    original_config = {
        "key_1": "${INTERPOLATION_A}",
        "key_2": "value_2",
        "dict_plain": {
            "key_1": "${INTERPOLATION_B}",
            "key_2": "value_2",
        },
        "dict_complex": {
            "key_1": "${INTERPOLATION_C}",
            "list_str": ["value_1", "${INTERPOLATION_D}"],
            "list_dict_str": [
                {
                    "k1": "${INTERPOLATION_E}",
                    "k2": "v2",
                },
                {
                    "k3": "v3",
                    "k4": "v4",
                },
            ],
        },
    }

    expected_config = {
        "key_1": environment["INTERPOLATION_A"],
        "key_2": "value_2",
        "dict_plain": {
            "key_1": environment["INTERPOLATION_B"],
            "key_2": "value_2",
        },
        "dict_complex": {
            "key_1": environment["INTERPOLATION_C"],
            "list_str": ["value_1", environment["INTERPOLATION_D"]],
            "list_dict_str": [
                {
                    "k1": environment["INTERPOLATION_E"],
                    "k2": "v2",
                },
                {
                    "k3": "v3",
                    "k4": "v4",
                },
            ],
        },
    }

    interpolator = Interpolator(environment=environment)
    config = interpolator.interpolate(config=original_config)
    print(json.dumps(config, indent=4))
    assert config is not original_config
    assert config == expected_config
