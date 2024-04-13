from datetime import datetime

from popyka.logging import LazyJson


def test_lazy_json_serializes_valid_instance():
    instance = {"key": "value"}
    lazy_json = LazyJson(instance)
    assert str(lazy_json) == '{\n    "key": "value"\n}'


def test_lazy_json_with_invalid_instance():
    instance = {"this-is", "a-set", datetime(2024, 4, 13, 13, 31, 31, 407204)}

    # Instantiation should work
    lazy_json = LazyJson(instance)

    # Serialization should fail
    returned_str = str(lazy_json)
    assert "datetime.datetime(2024, 4, 13, 13, 31, 31, 407204)" in returned_str
    assert "this-is" in returned_str
    assert "a-set" in returned_str
