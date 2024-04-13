import pytest

from popyka.config import FactoryMixin
from popyka.errors import ConfigError


class BaseTestClass:
    pass


class SampleImplClass(BaseTestClass):
    pass


def test_get_class_from_fqn_works():
    class_instance = FactoryMixin().get_class_from_fqn("tests.test_config_factory_mixin.SampleImplClass", BaseTestClass)
    assert class_instance is SampleImplClass


def test_get_class_from_fqn_fails_when_invalid_type():
    with pytest.raises(ConfigError, match=r".*is not a subclass of.*"):
        FactoryMixin().get_class_from_fqn("tests.test_config_factory_mixin.SampleImplClass", str)


def test_get_class_from_fqn_fails_when_invalid_module():
    with pytest.raises(ConfigError, match=r"^Module not found"):
        FactoryMixin().get_class_from_fqn("module.does.not.exist", str)


def test_get_class_from_fqn_fails_when_invalid_class():
    with pytest.raises(ConfigError, match=r"^Class not found"):
        FactoryMixin().get_class_from_fqn("tests.test_config_factory_mixin.ThisClassDoesNotExists", str)


def test_get_class_from_fqn_fails_when_invalid_characters():
    with pytest.raises(ConfigError, match=r"^Invalid fully qualified class name"):
        FactoryMixin().get_class_from_fqn("nopoints", str)
