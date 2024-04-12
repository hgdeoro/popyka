import pytest
import yaml

from popyka.config import ConfigError, FactoryMixin, FilterConfig, PopykaConfig


def test_parse_full_config():
    parsed_config = yaml.safe_load(
        """
database:
    connect_url: "postgresql://postgres:pass@localhost:54016/popyka_test"
    slot_name: some_psql_streaming_slot_name
filters:
    - class: popyka.builtin.filter.IncludeTable
      config:
        table_name_regex: "^django_.*"
    - class: popyka.builtin.filter.ExcludeTable
      config:
        tables: ["django_cache","django_audit"]
    - class: my.company.Filter
      config:
        transform: true
        max_size: 128
processors:
    - class: popyka.builtin.processor.ProduceToKafka
      filters:
        - class: popyka.builtin.filter.IncludeCrudOperation
          config:
            insert: true
      config:
        topic: "cdc_django"
        producer_config:
        - "bootstrap.servers": "server1:9092,server2:9092"
        - "client.id": client
"""
    )
    assert parsed_config.keys() == {"database", "filters", "processors"}
    assert parsed_config["database"].keys() == {"connect_url", "slot_name"}
    assert len(parsed_config["filters"]) == 3
    assert parsed_config["filters"][0]["class"] == "popyka.builtin.filter.IncludeTable"
    assert parsed_config["filters"][0]["config"]["table_name_regex"] == "^django_.*"

    config = PopykaConfig.from_yaml(parsed_config)
    assert config
    assert config.database.connect_url == "postgresql://postgres:pass@localhost:54016/popyka_test"
    assert config.database.slot_name == "some_psql_streaming_slot_name"
    assert config.filters[0].class_fqn == "popyka.builtin.filter.IncludeTable"
    assert config.filters[0].config_generic["table_name_regex"] == "^django_.*"
    assert config.processors[0].class_fqn == "popyka.builtin.processor.ProduceToKafka"
    assert config.processors[0].config_generic["topic"] == "cdc_django"
    assert config.processors[0].filters[0].class_fqn == "popyka.builtin.filter.IncludeCrudOperation"


class BaseTestClass:
    pass


class SampleImplClass(BaseTestClass):
    pass


def test_get_class_from_fqn_works():
    class_instance = FactoryMixin().get_class_from_fqn("tests.test_config.SampleImplClass", BaseTestClass)
    assert class_instance is SampleImplClass


def test_get_class_from_fqn_fails_when_invalid_type():
    with pytest.raises(ConfigError, match=r".*is not a subclass of.*"):
        FactoryMixin().get_class_from_fqn("tests.test_config.SampleImplClass", str)


def test_get_class_from_fqn_fails_when_invalid_module():
    with pytest.raises(ConfigError, match=r"^Module not found"):
        FactoryMixin().get_class_from_fqn("module.does.not.exist", str)


def test_get_class_from_fqn_fails_when_invalid_class():
    with pytest.raises(ConfigError, match=r"^Class not found"):
        FactoryMixin().get_class_from_fqn("tests.test_config.ThisClassDoesNotExists", str)


def test_get_class_from_fqn_fails_when_invalid_characters():
    with pytest.raises(ConfigError, match=r"^Invalid fully qualified class name"):
        FactoryMixin().get_class_from_fqn("nopoints", str)


def test_instantiate_builtin_ignore_tx_filter_works():
    filter_config = FilterConfig.from_yaml(
        {
            "class": "popyka.builtin.filters.IgnoreTxFilter",
            "config": {},
        }
    )
    instance = filter_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.filters.IgnoreTxFilter'>"
