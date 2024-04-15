import pytest

from popyka.config import ProcessorConfig
from popyka.errors import ConfigError


def test_instantiate_builtin_processor_log_change_processor_works():
    processor_config = ProcessorConfig.from_dict(
        {
            "class": "popyka.builtin.processors.LogChangeProcessor",
            "filters": [],
            "config": {},
        }
    )
    instance = processor_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.processors.LogChangeProcessor'>"


def test_instantiate_builtin_processor_log_change_processor_with_invalid_config_fails():
    processor_config = ProcessorConfig.from_dict(
        {
            "class": "popyka.builtin.processors.LogChangeProcessor",
            "filters": [],
            "config": {
                "key": "value",
            },
        }
    )
    with pytest.raises(ConfigError):
        processor_config.instantiate()


def test_instantiate_builtin_processor_produce_to_kafka_processor_works():
    processor_config = ProcessorConfig.from_dict(
        {
            "class": "popyka.builtin.processors.ProduceToKafkaProcessor",
            "filters": [],
            "config": {
                "topic": "cdc_django",
                "producer_config": {"bootstrap.servers": "server1:9092,server2:9092", "client.id": "client"},
            },
        }
    )
    assert processor_config.config_generic["topic"] == "cdc_django"
    assert processor_config.config_generic["producer_config"]["bootstrap.servers"] == "server1:9092,server2:9092"
    instance = processor_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.processors.ProduceToKafkaProcessor'>"


def test_instantiate_builtin_processor_produce_to_kafka_processor_without_bootstrap_server_fails():
    processor_config = ProcessorConfig.from_dict(
        {
            "class": "popyka.builtin.processors.ProduceToKafkaProcessor",
            "filters": [],
            "config": {
                "topic": "cdc_django",
                "producer_config": {"bootstrap.servers": "", "client.id": "client"},
            },
        }
    )
    with pytest.raises(ConfigError):
        processor_config.instantiate()
