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
filters:
    - class: popyka.default.filter.IncludeTable
      config:
        table_name_regex: "^django_.*"
    - class: popyka.default.filter.ExcludeTable
      config:
        tables: ["django_cache","django_audit"]
    - class: my.company.Filter
      config:
        transform: true
        max_size: 128
processors:
    - class: popyka.default.processor.ProduceToKafka
      config:
      - topic: "cdc_django"
      - producer_config:
        - "bootstrap.servers": "server1:9092,server2:9092"
        - "client.id": client
"""
    )
    assert parsed_config.keys() == {"database", "filters", "processors"}
    assert parsed_config["database"].keys() == {"connect_url"}
    assert len(parsed_config["filters"]) == 3
    assert parsed_config["filters"][0]["class"] == "popyka.default.filter.IncludeTable"
    assert parsed_config["filters"][0]["config"]["table_name_regex"] == "^django_.*"
