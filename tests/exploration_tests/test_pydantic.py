import json
from typing import Optional

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError


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


class SamplePopykaStrictConfig(SamplePopykaConfig):
    model_config: ConfigDict = ConfigDict(extra="forbid")


def test_serialize():
    config = SamplePopykaConfig(
        dsn="postgresql://...",
        filters=[SampleFilterConfig(class_fqn="some.Filter")],
        processors=[SampleProcessorConfig(class_fqn="some.Processor")],
    )
    print(config.model_dump())
    print(config.model_dump_json(indent=4))


def test_deserialize():
    deserialized = {
        "dsn": "postgresql://...",
        "filters": [{"class_fqn": "some.Filter"}],
        "processors": [{"class_fqn": "some.Processor"}],
    }
    config = SamplePopykaConfig(**deserialized)
    print(config)


def test_deserialize_extra_keys():
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
