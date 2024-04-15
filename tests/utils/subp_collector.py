import io
import json
import logging
import re
import subprocess
import threading
import time
from functools import cached_property

from popyka.core import Wal2JsonV2Change

logger = logging.getLogger(__name__)

logger_stdout_to_list = logging.getLogger("STDOUT")


class AssertableChange(Wal2JsonV2Change):
    def assert_table(self, table: str) -> "AssertableChange":
        assert self["table"] == table
        return self

    def assert_insert(self) -> "AssertableChange":
        assert self["action"] == "I"
        return self

    def assert_update(self) -> "AssertableChange":
        assert self["action"] == "U"
        return self

    def assert_delete(self) -> "AssertableChange":
        assert self["action"] == "D"
        return self


def stdout_to_list(buffered_reader: io.BufferedReader, target_list: list[str]):
    while True:
        line: bytes = buffered_reader.readline()
        if line in ("", b""):
            return
        line: str = line.decode("utf-8", errors="replace").rstrip()
        logger_stdout_to_list.debug(">>> %s", line)
        target_list.append(line)


class SubProcCollector:
    def __init__(self, args):
        self._args = args
        self._proc: subprocess.Popen | None = None
        self._stdout: list[str] = []
        self._thread_stdout: threading.Thread | None = None
        self._thread_stderr: threading.Thread | None = None
        self._stdout_start_at: int = 0

    def poll(self) -> int | None:
        return self._proc.poll()

    def kill(self):
        return self._proc.kill()

    def wait(self, timeout=None):
        return self._proc.wait(timeout=timeout)

    @property
    def stdout(self):
        return self._stdout

    def join_threads(self):
        assert self._thread_stdout is not None
        assert self._thread_stderr is not None
        self._thread_stdout.join()
        self._thread_stderr.join()

    def wait_for(self, text: str, timeout=30.0, from_beginning=False):
        assert timeout is not None
        timeout = float(timeout)
        start_time = time.monotonic()
        print(f"Waiting for: '{text}'")

        while time.monotonic() - start_time < timeout:
            for line_num in range(0 if from_beginning else self._stdout_start_at, len(self._stdout)):
                if not from_beginning:
                    self._stdout_start_at = line_num + 1
                logger.debug("wait_for('%s') - line: '%s'", text, self._stdout[line_num])
                if text in self._stdout[line_num]:
                    return self._stdout[line_num]
            time.sleep(0.01)

        raise TimeoutError(f"Timeout. Not found: {text}")

    @cached_property
    def _change_regex(self):
        pattern = r"^INFO:popyka.builtin.processors.LogChangeProcessor:Change received: ({.*})$"
        return re.compile(pattern)

    def _get_change(self, line: str) -> dict | None:
        matched = self._change_regex.fullmatch(line)
        if matched:
            matched_str = matched.group(1)
            logger.debug("_get_change(): matched: '%s'", matched_str)
            return json.loads(matched_str)

    def wait_for_change(self, timeout=30.0, from_beginning=False):
        assert timeout is not None
        timeout = float(timeout)
        start_time = time.monotonic()
        print("Waiting for change...")

        while time.monotonic() - start_time < timeout:
            for line_num in range(0 if from_beginning else self._stdout_start_at, len(self._stdout)):
                if not from_beginning:
                    self._stdout_start_at = line_num + 1
                logger.debug("wait_for_change() - line: '%s'", self._stdout[line_num])
                change = self._get_change(self._stdout[line_num])
                if change is not None:
                    return AssertableChange(change)
            time.sleep(0.01)

        raise TimeoutError("Timeout. Change not found")

    def start(self) -> "SubProcCollector":
        self._proc = subprocess.Popen(args=self._args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self._thread_stdout = threading.Thread(
            target=stdout_to_list, args=[self._proc.stdout, self._stdout], daemon=True
        )
        self._thread_stderr = threading.Thread(
            target=stdout_to_list, args=[self._proc.stderr, self._stdout], daemon=True
        )
        self._thread_stdout.start()
        self._thread_stderr.start()
        return self
