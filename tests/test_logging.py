from datetime import datetime

import pytest

from popyka.logging import LazyJson


def test_lazy_json_serializes_valid_instance():
    instance = {"key": "value"}
    lazy_json = LazyJson(instance)
    assert str(lazy_json) == '{\n    "key": "value"\n}'


def test_lazy_json_with_invalid_instance():
    instance = {"this", "is", "a", "set", datetime.now()}

    # Instantiation should work
    lazy_json = LazyJson(instance)

    # Serialization should fail
    with pytest.raises(TypeError, match=r"Object of type set is not JSON serializable"):
        str(lazy_json)
