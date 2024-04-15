import pathlib
import time

import pytest

from popyka.builtin.processors import LogChangeProcessor
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


PYTHON_CODE_HELLO_WORLD = """
print("HELLO")
print("WORLD")
"""


PYTHON_CODE_LOG_CHANGE_PROCESSOR = """
import logging
logging.basicConfig(level=logging.INFO)

from popyka.builtin.processors import LogChangeProcessor
lcp = LogChangeProcessor(config_generic={})
lcp.process_change(change={"key": "value"})
"""


class TestParseLogChangeProcessorOutput:
    def test_use_lcp_directly(self):
        lcp = LogChangeProcessor(config_generic={})
        lcp.process_change(change={"key": "value"})

    def test_hello_world(self, tmp_path: pathlib.Path):
        python_script = tmp_path / "sample.py"
        python_script.write_text(PYTHON_CODE_HELLO_WORLD)

        sp = SubProcCollector(args=["python3", str(python_script.absolute())])
        sp.start()
        sp.wait(timeout=1)
        print(sp.stdout)
        print(sp.stderr)
        sp.wait_for("HELLO", timeout=0.5)
        sp.wait_for("WORLD", timeout=0.5)

    def test_python_code_lcp_works(self, tmp_path: pathlib.Path):
        python_script = tmp_path / "sample.py"
        python_script.write_text(PYTHON_CODE_LOG_CHANGE_PROCESSOR)

        sp = SubProcCollector(
            args=["env", "PYTHONPATH=.", "LAZYTOSTR_COMPACT=1", "python3", str(python_script.absolute())]
        )
        sp.start()
        sp.wait(timeout=1)
        print(sp.stdout)
        print(sp.stderr)
        sp.wait_for("INFO:popyka.builtin.processors.LogChangeProcessor:LogChangeProcessor", timeout=0.5)


PYTHON_CODE_STDOUT_STDERR = """
import sys
print("this-is-stdout")
print("this-is-stderr", file=sys.stderr)
"""


def test_stdout_stderr(tmp_path: pathlib.Path):
    python_script = tmp_path / "sample.py"
    python_script.write_text(PYTHON_CODE_STDOUT_STDERR)

    sp = SubProcCollector(args=["python3", str(python_script.absolute())])
    sp.start()
    sp.wait(timeout=1)
    print(sp.stdout)
    print(sp.stderr)
    sp.wait_for("this-is-stdout", timeout=0.5)
    sp.wait_for("this-is-stderr", timeout=0.5)
