import json

import yaml

from tests.conftest import exploration_test


@exploration_test
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
