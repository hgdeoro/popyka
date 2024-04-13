import dataclasses
import importlib
import pathlib

import yaml

from popyka.core import Filter, Processor
from popyka.errors import ConfigError
from popyka.interpolation import Interpolator


class FactoryMixin:
    @classmethod
    def get_class_from_fqn(cls, fqn: str, expected_type: type):
        split_result = fqn.rsplit(".", maxsplit=1)
        if len(split_result) != 2:
            raise ConfigError(f"Invalid fully qualified class name: '{fqn}'")

        module_name, class_name = split_result
        try:
            module_instance = importlib.import_module(module_name)
        except ModuleNotFoundError:
            raise ConfigError(f"Module not found: '{module_name}'. fqn: '{fqn}'")

        try:
            class_instance = getattr(module_instance, class_name)
        except AttributeError:
            raise ConfigError(f"Class not found: '{class_name}'. fqn: '{fqn}'")

        if not issubclass(class_instance, expected_type):
            raise ConfigError(f"The class '{fqn}' is not a subclass of '{expected_type}'. fqn: '{fqn}'")
        return class_instance

    def instantiate(self):
        raise NotImplementedError()


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
class FilterConfig(FactoryMixin):
    class_fqn: str
    config_generic: dict

    @classmethod
    def from_yaml(cls, config: dict) -> "FilterConfig":
        class_fqn = config["class"]
        config_generic = config["config"]
        assert isinstance(class_fqn, str)
        assert isinstance(config_generic, dict)
        return FilterConfig(
            class_fqn=class_fqn,
            config_generic=config_generic,
        )

    def instantiate(self) -> Filter:
        """Creates an instance of `Filter` based on configuration"""
        filter_class = self.get_class_from_fqn(self.class_fqn, Filter)
        instance = filter_class(self.config_generic)
        # instance.setup()  # This is an idea, maybe we should have an explicit method to run business logic
        # to avoid doing it on __init__()
        return instance


@dataclasses.dataclass
class ProcessorConfig(FactoryMixin):
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

    def instantiate(self) -> Processor:
        """Creates an instance of `Processor` based on configuration"""
        processor_class = self.get_class_from_fqn(self.class_fqn, Processor)
        instance = processor_class(self.config_generic)
        # instance.setup()  # This is an idea, maybe we should have an explicit method to run business logic
        # to avoid doing it on __init__()
        return instance


@dataclasses.dataclass
class PopykaConfig:
    database: DatabaseConfig
    filters: list[FilterConfig]
    processors: list[ProcessorConfig]

    @classmethod
    def from_yaml(cls, config: dict, environment: dict[str, str] = None) -> "PopykaConfig":
        # FIXME: a better name would be 'from_dict()'
        interpolated = Interpolator(environment=environment or {}).interpolate(config)
        database_config = DatabaseConfig.from_yaml(interpolated["database"])
        filters = [FilterConfig.from_yaml(_) for _ in interpolated["filters"]]
        processors = [ProcessorConfig.from_yaml(_) for _ in interpolated["processors"]]
        return PopykaConfig(
            database=database_config,
            filters=filters,
            processors=processors,
        )

    @classmethod
    def get_default_config(cls, environment=None) -> "PopykaConfig":
        config_path = pathlib.Path(__file__).parent / "popyka-default.yaml"
        config_dict = yaml.safe_load(config_path.read_text())
        return PopykaConfig.from_yaml(config_dict, environment=environment)
