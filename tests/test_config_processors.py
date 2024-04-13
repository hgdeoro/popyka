from popyka.config import ProcessorConfig


def test_instantiate_builtin_processor_log_change_processor_works():
    processor_config = ProcessorConfig.from_yaml(
        {
            "class": "popyka.builtin.processors.LogChangeProcessor",
            "filters": [],
            "config": {},
        }
    )
    instance = processor_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.processors.LogChangeProcessor'>"


def test_instantiate_builtin_processor_produce_to_kafka_processor_works():
    processor_config = ProcessorConfig.from_yaml(
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
