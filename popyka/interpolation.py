import copy
import typing
from types import NoneType

SupportedTypes = typing.Union[list, set, dict, str, bool, int, float, NoneType]


class Interpolator:
    # FIXME: add to user doc the yaml data types that are supported
    def __init__(self, environment: dict[str, str]):
        assert environment is not None
        self._environment = environment

    def _interpolate_list(self, element: list) -> list:
        assert isinstance(element, list)
        return [self._interpolate(_) for _ in element]

    def _interpolate_set(self, element: set) -> set:
        assert isinstance(element, set)
        return {self._interpolate(_) for _ in element}

    def _interpolate_dict(self, element: dict) -> dict:
        assert isinstance(element, dict)
        return {key: self._interpolate(value) for key, value in element.items()}

    def _interpolate_str(self, element: str) -> str:
        assert isinstance(element, str)
        for env_key, env_value in self._environment.items():
            element = element.replace("${" + env_key + "}", env_value)
        return element

    def _interpolate(self, element: SupportedTypes) -> SupportedTypes:
        if isinstance(element, list):
            return self._interpolate_list(element)
        elif isinstance(element, dict):
            return self._interpolate_dict(element)
        elif isinstance(element, set):
            return self._interpolate_set(element)
        elif isinstance(element, str):
            return self._interpolate_str(element)
        elif isinstance(element, (bool, int, float, NoneType)):
            return element
        else:
            raise NotImplementedError(f"Cannot do interpolation on element of type {type(element)}: {element}")

    def interpolate(self, config: dict) -> dict:
        assert isinstance(config, dict)
        interpolated_config = copy.deepcopy(config)
        interpolated_config = self._interpolate(interpolated_config)
        return interpolated_config
