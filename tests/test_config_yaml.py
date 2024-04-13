import yaml

from popyka.config import PopykaConfig


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

    config = PopykaConfig.from_dict(parsed_config)
    assert config
    assert config.database.connect_url == "postgresql://postgres:pass@localhost:54016/popyka_test"
    assert config.database.slot_name == "some_psql_streaming_slot_name"
    assert config.filters[0].class_fqn == "popyka.builtin.filter.IncludeTable"
    assert config.filters[0].config_generic["table_name_regex"] == "^django_.*"
    assert config.processors[0].class_fqn == "popyka.builtin.processor.ProduceToKafka"
    assert config.processors[0].config_generic["topic"] == "cdc_django"
    assert config.processors[0].filters[0].class_fqn == "popyka.builtin.filter.IncludeCrudOperation"
