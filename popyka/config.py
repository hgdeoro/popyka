import dataclasses
import importlib
import logging
import pathlib

import yaml

from popyka.core import Filter, Processor
from popyka.errors import ConfigError
from popyka.interpolation import Interpolator

logger = logging.getLogger(__name__)


class FactoryMixin:
    """Mixin for components that needs to create instances of classes"""

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
    def from_dict(cls, config: dict) -> "DatabaseConfig":
        return DatabaseConfig(
            connect_url=config["connect_url"],
            slot_name=config["slot_name"],
        )


@dataclasses.dataclass
class FilterConfig(FactoryMixin):
    class_fqn: str
    config_generic: dict

    @classmethod
    def from_dict(cls, config: dict) -> "FilterConfig":
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
        instance: Filter = filter_class(self.config_generic)
        instance.setup()
        return instance


@dataclasses.dataclass
class ProcessorConfig(FactoryMixin):
    class_fqn: str
    filters: list[FilterConfig]
    config_generic: dict

    @classmethod
    def from_dict(cls, config: dict) -> "ProcessorConfig":
        class_fqn = config["class"]
        filters = [FilterConfig.from_dict(_) for _ in config.get("filters", []) or []]
        config_generic = config["config"]
        return ProcessorConfig(
            class_fqn=class_fqn,
            filters=filters,
            config_generic=config_generic,
        )

    def instantiate(self) -> Processor:
        """Creates an instance of `Processor` based on configuration"""
        processor_class = self.get_class_from_fqn(self.class_fqn, Processor)
        instance: Processor = processor_class(self.config_generic)
        instance.setup()
        return instance


@dataclasses.dataclass
class PopykaConfig:
    database: DatabaseConfig
    filters: list[FilterConfig]
    processors: list[ProcessorConfig]

    @classmethod
    def from_dict(cls, config: dict, environment: dict[str, str] = None) -> "PopykaConfig":
        interpolated = Interpolator(environment=environment or {}).interpolate(config)
        database_config = DatabaseConfig.from_dict(interpolated.get("database", None))
        filters = [FilterConfig.from_dict(_) for _ in interpolated.get("filters", []) or []]
        processors = [ProcessorConfig.from_dict(_) for _ in interpolated.get("processors", []) or []]

        if database_config is None:
            raise ConfigError("Invalid config: `database` is required")

        if not processors:
            # TODO: is there any situation when running without processors is ok?
            raise ConfigError("Invalid config: refuse to run without any processor. Check `processors` in config.")

        return PopykaConfig(
            database=database_config,
            filters=filters,
            processors=processors,
        )

    @classmethod
    def get_config_file_path(cls, environment=None) -> pathlib.Path:
        custom_config = environment.get("POPYKA_CONFIG")
        if custom_config is None:
            config_path = pathlib.Path(__file__).parent / "popyka-default.yaml"
            return config_path
        else:
            logger.info("Using custom config file. POPYKA_CONFIG=%s", custom_config)
            config_path = pathlib.Path(custom_config).absolute()
            if not config_path.exists():
                raise ConfigError(f"Invalid config: {custom_config} (POPYKA_CONFIG) does not exists")
            if config_path.is_dir():
                raise ConfigError(f"Invalid config: {custom_config} (POPYKA_CONFIG) is a directory")
            if not config_path.is_file():
                logger.warning("POPYKA_CONFIG=%s is not a regular file", custom_config)
            return config_path

    @classmethod
    def get_config(cls, environment=None) -> "PopykaConfig":
        config_path = cls.get_config_file_path(environment=environment)
        config_dict = yaml.safe_load(config_path.read_text())
        return PopykaConfig.from_dict(config_dict, environment=environment)
