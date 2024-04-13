import json
import uuid

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
