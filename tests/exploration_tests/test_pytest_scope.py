import uuid

import pytest

from tests.conftest import exploration_test


@pytest.fixture(scope="function")
def fixture_1() -> str:
    value = str(uuid.uuid4())
    print(f"fixture_1(): value={value}")
    return value


@pytest.fixture(scope="function")
def fixture_2() -> str:
    value = str(uuid.uuid4())
    print(f"fixture_2(): value={value}")
    return value


@pytest.fixture(scope="function")
def fixture_3(fixture_1, fixture_2) -> str:
    value = str(uuid.uuid4())
    print(f"fixture_3(): fixture_1={fixture_1} fixture_2={fixture_2} value={value}")
    return value


@pytest.mark.skip
@exploration_test
def test_1(fixture_1, fixture_2, fixture_3):
    print(f"test_1(): {fixture_1}")
    print(f"test_1(): {fixture_2}")
    print(f"test_1(): {fixture_3}")


@pytest.mark.skip
@exploration_test
def test_2(fixture_1, fixture_2, fixture_3):
    print(f"test_2(): {fixture_1}")
    print(f"test_2(): {fixture_2}")
    print(f"test_2(): {fixture_3}")
