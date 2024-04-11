import dataclasses
import json
import pathlib

import yaml

DIR = pathlib.Path(__file__).parent


def test_yaml_1():
    parsed_config = yaml.safe_load(
        """
kafka:
  database:
    connect_url: "postgresql://postgres:pass@localhost:54016/popyka_test"
  producer:
    config:
      "bootstrap.servers": server1:9092,server2:9092
      "client.id": client
"""
    )
    json_dump = json.dumps(parsed_config, sort_keys=True, indent=4)
    print(json_dump)
    assert json_dump == json.dumps(
        {
            "kafka": {
                "database": {"connect_url": "postgresql://postgres:pass@localhost:54016/popyka_test"},
                "producer": {"config": {"bootstrap.servers": "server1:9092,server2:9092", "client.id": "client"}},
            }
        },
        sort_keys=True,
        indent=4,
    )


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


@dataclasses.dataclass
class DatabaseConfig:
    connect_url: str
    slot_name: str

    @classmethod
    def from_yaml(cls, config: dict) -> "DatabaseConfig":
        return DatabaseConfig(
            connect_url=config["connect_url"],
            slot_name=config["slot_name"],
        )


@dataclasses.dataclass
class FilterConfig:
    class_fqn: str
    config_generic: dict

    @classmethod
    def from_yaml(cls, config: dict) -> "FilterConfig":
        class_fqn = config["class"]
        config_generic = config["config"]
        return FilterConfig(
            class_fqn=class_fqn,
            config_generic=config_generic,
        )


@dataclasses.dataclass
class ProcessorConfig:
    class_fqn: str
    filters: list[FilterConfig]
    config_generic: dict

    @classmethod
    def from_yaml(cls, config: dict) -> "ProcessorConfig":
        class_fqn = config["class"]
        filters = [FilterConfig.from_yaml(_) for _ in config["filters"]]
        config_generic = config["config"]
        return ProcessorConfig(
            class_fqn=class_fqn,
            filters=filters,
            config_generic=config_generic,
        )


@dataclasses.dataclass
class PopykaConfig:
    database: DatabaseConfig
    filters: list[FilterConfig]
    processors: list[ProcessorConfig]

    @classmethod
    def from_yaml(cls, config: dict) -> "PopykaConfig":
        database_config = DatabaseConfig.from_yaml(config["database"])
        filters = [FilterConfig.from_yaml(_) for _ in config["filters"]]
        processors = [ProcessorConfig.from_yaml(_) for _ in config["processors"]]
        return PopykaConfig(
            database=database_config,
            filters=filters,
            processors=processors,
        )
