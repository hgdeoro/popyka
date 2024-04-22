import pathlib
import time

import pytest

from tests.conftest import slow_test
from tests.utils.subp_collector import SubProcCollector

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


@slow_test
def test_short():
    sp = SubProcCollector(args=["vmstat", "1", "2"])
    sp.start()
    while sp.poll() is None:
        print(f"STDOUT: {len(sp.stdout)}")
        time.sleep(0.1)


@slow_test
def test_long():
    sp = SubProcCollector(args=["vmstat", "1", "120"])
    sp.start()
    while sp.poll() is None:
        print(f"STDOUT: {len(sp.stdout)}")

        if len(sp.stdout) >= 4:
            sp.kill()
        time.sleep(0.1)


@pytest.fixture()
def subp_instance() -> SubProcCollector:
    sp = SubProcCollector(args=["/bin/bash", "-c", f"echo '{OUTPUT}'"])
    sp.start()
    assert sp.wait(timeout=1) == 0
    return sp


def test_stdout_stderr(tmp_path: pathlib.Path):
    python_script = tmp_path / "sample.py"
    python_script.write_text(
        """
import sys
print("this-is-stdout")
print("this-is-stderr", file=sys.stderr)
sys.exit(0)
"""
    )

    sp = SubProcCollector(args=["python3", str(python_script.absolute())])
    sp.start()
    assert sp.wait(timeout=1) == 0
    print(sp.stdout)
    sp.wait_for("this-is-stdout", timeout=0.5, from_beginning=True)
    sp.wait_for("this-is-stderr", timeout=0.5, from_beginning=True)


class TestWaitFor:
    def test_all_output_lines_exists(self, subp_instance: SubProcCollector):
        for line in OUTPUT_LINES:
            subp_instance.wait_for(line, timeout=0.1)

    def test_find_lines_sequentially(self, subp_instance: SubProcCollector):
        subp_instance.wait_for(OUTPUT_LINES[2], timeout=0.1)
        subp_instance.wait_for(OUTPUT_LINES[4], timeout=0.1)
        subp_instance.wait_for(OUTPUT_LINES[6], timeout=0.1)

    def test_seek_advances(self, subp_instance: SubProcCollector):
        subp_instance.wait_for(OUTPUT_LINES[-1], timeout=0.1)
        with pytest.raises(TimeoutError):
            subp_instance.wait_for(OUTPUT_LINES[-1], timeout=0.1)

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


class TestParseLogChangeProcessorOutput:
    def test_run_python(self, tmp_path: pathlib.Path):
        python_script = tmp_path / "sample.py"
        python_script.write_text(
            """
print("HELLO")
print("WORLD")
"""
        )

        sp = SubProcCollector(args=["python3", str(python_script.absolute())])
        sp.start()
        assert sp.wait(timeout=1) == 0
        print(sp.stdout)
        sp.wait_for("HELLO", timeout=0.5)
        sp.wait_for("WORLD", timeout=0.5)

    PYTHON_CODE_LOG_CHANGE_PROCESSOR = """
import logging
logging.basicConfig(level=logging.INFO)

from popyka.builtin.processors import LogChangeProcessor
lcp = LogChangeProcessor(config_generic={})
lcp.process_change(change={"key": "some-value"})
    """

    def test_wait_for_change(self, tmp_path: pathlib.Path):
        python_script = tmp_path / "sample.py"
        python_script.write_text(self.PYTHON_CODE_LOG_CHANGE_PROCESSOR)

        sp = SubProcCollector(
            args=["env", "PYTHONPATH=.", "POPYKA_COMPACT_DUMP=1", "python3", str(python_script.absolute())]
        )
        sp.start()
        assert sp.wait(timeout=1) == 0
        print(sp.stdout)

        change = sp.wait_for_change(timeout=0.1)
        assert change == {"key": "some-value"}

        with pytest.raises(TimeoutError):
            sp.wait_for_change(timeout=0.1)
