import dataclasses


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
