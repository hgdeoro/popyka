import copy


class Interpolator:
    def __init__(self, environment: dict[str, str]):
        self._environment = environment

    def _interpolate_list(self, element: list) -> list:
        assert isinstance(element, list)
        for i in range(len(element)):
            element[i] = self._interpolate(element[i])
        return element

    def _interpolate_dict(self, element: dict) -> dict:
        assert isinstance(element, dict)
        for key in element.keys():
            value = element[key]
            new_value = self._interpolate(value)
            element[key] = new_value
        return element

    def _interpolate_str(self, element: str) -> str:
        assert isinstance(element, str)
        for env_key, env_value in self._environment.items():
            element = element.replace("${" + env_key + "}", env_value)
        return element

    def _interpolate(self, element: [list, dict, str, bool, int]) -> list | dict | str | bool | int:
        if isinstance(element, list):
            return self._interpolate_list(element)
        elif isinstance(element, dict):
            return self._interpolate_dict(element)
        elif isinstance(element, str):
            return self._interpolate_str(element)
        elif isinstance(element, (bool, int)):
            return element
        else:
            raise NotImplementedError(f"Cannot do interpolation on element of type {type(element)}: {element}")

    def interpolate(self, config: dict) -> dict:
        assert isinstance(config, dict)
        interpolated_config = copy.deepcopy(config)
        interpolated_config = self._interpolate(interpolated_config)
        return interpolated_config
