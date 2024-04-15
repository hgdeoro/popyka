import time

import pytest

from tests.conftest import slow_test
from tests.utils.subp_collector import SubProcCollector


@slow_test
def test_short():
    sp = SubProcCollector(args=["vmstat", "1", "2"])
    sp.start()
    while sp.poll() is None:
        print(f"STDOUT: {len(sp.stdout)}")
        print(f"STDERR: {len(sp.stderr)}")
        time.sleep(0.1)


@slow_test
def test_long():
    sp = SubProcCollector(args=["vmstat", "1", "120"])
    sp.start()
    while sp.poll() is None:
        print(f"STDOUT: {len(sp.stdout)}")
        print(f"STDERR: {len(sp.stderr)}")

        if len(sp.stdout) >= 4:
            sp.kill()
        time.sleep(0.1)


@pytest.fixture()
def subp_instance() -> SubProcCollector:
    sp = SubProcCollector(args=["/bin/sh", "-c", f"echo {OUTPUT}"])
    sp.start()
    sp.wait(timeout=1)
    return sp


OUTPUT = """
line-0
line-1
line-2
line-3
line-4
line-5
line-6
""".strip()

OUTPUT_LINES = [_.strip() for _ in OUTPUT.splitlines() if _.strip()]


class TestWaitFor:
    def test_all_output_lines_exists(self, subp_instance: SubProcCollector):
        for line in OUTPUT_LINES:
            subp_instance.wait_for(line, timeout=0.1)

    def test_find_lines_sequentially(self, subp_instance: SubProcCollector):
        subp_instance.wait_for(OUTPUT_LINES[2], timeout=0.1)
        subp_instance.wait_for(OUTPUT_LINES[4], timeout=0.1)
        subp_instance.wait_for(OUTPUT_LINES[6], timeout=0.1)

    def test_fails_when_reversed_order(self, subp_instance: SubProcCollector):
        subp_instance.wait_for(OUTPUT_LINES[4], timeout=0.1)
        with pytest.raises(TimeoutError):
            subp_instance.wait_for(OUTPUT_LINES[2], timeout=0.1)

    def test_timeout_when_not_found(self, subp_instance: SubProcCollector):
        with pytest.raises(TimeoutError):
            subp_instance.wait_for("this-line-does-not-exists", timeout=0.1)

    def test_seeks_when_not_found(self, subp_instance: SubProcCollector):
        with pytest.raises(TimeoutError):
            subp_instance.wait_for("this-line-does-not-exists", timeout=0.1)
        with pytest.raises(TimeoutError):
            subp_instance.wait_for(OUTPUT_LINES[2], timeout=0.1)
