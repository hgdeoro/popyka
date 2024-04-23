import json
from typing import Optional

from pydantic import BaseModel


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


def test_serialize():
    config = SamplePopykaConfig(
        dsn="postgresql://...",
        filters=[SampleFilterConfig(class_fqn="some.Filter")],
        processors=[SampleProcessorConfig(class_fqn="some.Processor")],
    )
    print(config.model_dump())
    print(config.model_dump_json(indent=4))


def test_deserialize():
    deserialized = json.loads(
        """
    {
        "dsn": "postgresql://...",
        "filters": [
            {
                "class_fqn": "some.Filter"
            }
        ],
        "processors": [
            {
                "class_fqn": "some.Processor"
            }
        ]
    }
    """
    )
    config = SamplePopykaConfig(**deserialized)
    print(config)
