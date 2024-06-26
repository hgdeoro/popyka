import json
from typing import Optional

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from tests.conftest import exploration_test


class SampleFilterConfig(BaseModel):
    class_fqn: str
    config: Optional[dict] = None


class SampleProcessorConfig(BaseModel):
    class_fqn: str
    config: Optional[dict] = None


class SamplePopykaConfig(BaseModel):
    dsn: str
    filters: list[SampleFilterConfig]
    processors: list[SampleProcessorConfig]


@exploration_test
class TestRelaxedConfig:
    def test_serialize_simple(self):
        config = SamplePopykaConfig(
            dsn="postgresql://...",
            filters=[SampleFilterConfig(class_fqn="some.Filter")],
            processors=[SampleProcessorConfig(class_fqn="some.Processor")],
        )
        print(config.model_dump_json(indent=4))

    def test_deserialize_simple(self):
        deserialized = {
            "dsn": "postgresql://...",
            "filters": [
                {"class_fqn": "some.Filter"},
            ],
            "processors": [{"class_fqn": "some.Processor"}],
        }
        config = SamplePopykaConfig(**deserialized)
        print(config.model_dump_json(indent=4))


class SampleFilterStrictConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(extra="forbid")
    class_fqn: str
    config: Optional[dict] = None


class SampleProcessorStrictConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(extra="forbid")
    class_fqn: str
    config: Optional[dict] = None


class SamplePopykaStrictConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(extra="forbid")
    dsn: str
    filters: list[SampleFilterStrictConfig]
    processors: list[SampleProcessorStrictConfig]


@exploration_test
class TestStrictConfig:
    def test_deserialize_strict_extra_keys(self):
        deserialized = {
            "dsn": "postgresql://...",
            "filters": [{"class_fqn": "some.Filter"}],
            "processors": [{"class_fqn": "some.Processor"}],
            "extra_key": [],
        }
        assert SamplePopykaConfig(**deserialized)

        with pytest.raises(ValidationError) as err:
            SamplePopykaStrictConfig(**deserialized)

        assert json.loads(err.value.json())[0]["loc"][0] == "extra_key"

    def test_serialize_strict_complex(self):
        config = SamplePopykaStrictConfig(
            dsn="postgresql://...",
            filters=[
                SampleFilterStrictConfig(
                    class_fqn="some.Filter",
                    config={
                        "key1": "value1",
                        "key2": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                        "key3": {"subkey": [None]},
                    },
                )
            ],
            processors=[SampleProcessorStrictConfig(class_fqn="some.Processor")],
        )
        print(config.model_dump_json(indent=4))

    def test_deserialize_strict_complex(self):
        deserialized = {
            "dsn": "postgresql://...",
            "filters": [
                {
                    "class_fqn": "some.Filter",
                },
                {
                    "class_fqn": "some.other.Filter",
                    "config": {
                        "this-is": "free-form-dict",
                        "key1": 1234,
                        "key2": [1, 2, 3],
                        "key3": {
                            "sub1": None,
                        },
                    },
                },
            ],
            "processors": [
                {
                    "class_fqn": "some.Processor",
                },
            ],
        }
        config = SamplePopykaStrictConfig(**deserialized)
        print(config.model_dump_json(indent=4))
