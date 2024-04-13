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
        self._proc: subprocess.Popen = None
        self._stdout: list[str] = []
        self._stderr: list[str] = []
        self._thread_stdout = None
        self._thread_stderr = None

    def poll(self) -> int | None:
        return self._proc.poll()

    def kill(self):
        return self._proc.kill()

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def wait_for(self, text: str, timeout=None):
        start_time = time.monotonic()
        print(f"Waiting for: '{text}'")
        while timeout is None or time.monotonic() - start_time < timeout:
            for line in self._stdout:
                if text in line:
                    return
            for line in self._stderr:
                if text in line:
                    return
            time.sleep(0.01)
        raise Exception(f"Timeout. Not found: {text}")

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
