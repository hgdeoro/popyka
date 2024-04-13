import pytest

from popyka.config import FactoryMixin, PopykaConfig
from popyka.errors import ConfigError


class BaseTestClass:
    pass


class SampleImplClass(BaseTestClass):
    pass


def test_get_class_from_fqn_works():
    class_instance = FactoryMixin().get_class_from_fqn("tests.test_config.SampleImplClass", BaseTestClass)
    assert class_instance is SampleImplClass


def test_get_class_from_fqn_fails_when_invalid_type():
    with pytest.raises(ConfigError, match=r".*is not a subclass of.*"):
        FactoryMixin().get_class_from_fqn("tests.test_config.SampleImplClass", str)


def test_get_class_from_fqn_fails_when_invalid_module():
    with pytest.raises(ConfigError, match=r"^Module not found"):
        FactoryMixin().get_class_from_fqn("module.does.not.exist", str)


def test_get_class_from_fqn_fails_when_invalid_class():
    with pytest.raises(ConfigError, match=r"^Class not found"):
        FactoryMixin().get_class_from_fqn("tests.test_config.ThisClassDoesNotExists", str)


def test_get_class_from_fqn_fails_when_invalid_characters():
    with pytest.raises(ConfigError, match=r"^Invalid fully qualified class name"):
        FactoryMixin().get_class_from_fqn("nopoints", str)


def test_default_config_with_fixture(popyka_env_vars):
    # Default config is expected to WORK when the fixture `popyka_env_vars` is used
    default_config = PopykaConfig.get_default_config(environment=popyka_env_vars)
    assert default_config


def test_default_config_without_fixture():
    # Default config is expected to FAIL without `popyka_env_vars`
    with pytest.raises(ConfigError):
        PopykaConfig.get_default_config(environment={})
