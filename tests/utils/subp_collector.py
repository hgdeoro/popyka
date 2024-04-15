import io
import logging
import subprocess
import threading
import time

logger = logging.getLogger(__name__)


def _read_into_list(buffered_reader: io.BufferedReader, target_list: list[str]):
    while True:
        line: bytes = buffered_reader.readline()
        if line in ("", b""):
            return
        line: str = line.decode("utf-8", errors="replace").rstrip()
        logger.debug("> %s", line)
        target_list.append(line)


class SubProcCollector:
    def __init__(self, args):
        self._args = args
        self._proc: subprocess.Popen | None = None
        self._stdout: list[str] = []
        self._stderr: list[str] = []
        self._thread_stdout: threading.Thread | None = None
        self._thread_stderr: threading.Thread | None = None
        self._stdout_line_last_found: int = 0
        self._stderr_line_last_found: int = 0

    def poll(self) -> int | None:
        return self._proc.poll()

    def kill(self):
        return self._proc.kill()

    def wait(self, timeout=None):
        return self._proc.wait(timeout=timeout)

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def join_threads(self):
        self._thread_stdout.join()
        self._thread_stderr.join()

    def wait_for(self, text: str, timeout=30.0):
        assert timeout is not None
        timeout = float(timeout)
        start_time = time.monotonic()
        print(f"Waiting for: '{text}'")
        while time.monotonic() - start_time < timeout:
            for line_num in range(self._stdout_line_last_found, len(self._stdout)):
                self._stdout_line_last_found = line_num
                line = self._stdout[line_num]
                if text in line:
                    return line

            for line_num in range(self._stderr_line_last_found, len(self._stderr)):
                self._stderr_line_last_found = line_num
                line = self._stderr[line_num]
                if text in line:
                    return line
            time.sleep(0.01)
        raise TimeoutError(f"Timeout. Not found: {text}")

    def start(self) -> "SubProcCollector":
        self._proc = subprocess.Popen(args=self._args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self._thread_stdout = threading.Thread(
            target=_read_into_list, args=[self._proc.stdout, self._stdout], daemon=True
        )
        self._thread_stderr = threading.Thread(
            target=_read_into_list, args=[self._proc.stderr, self._stderr], daemon=True
        )
        self._thread_stdout.start()
        self._thread_stderr.start()
        return self
