import io
import logging
import subprocess
import threading

logger = logging.getLogger(__name__)


def _read_into_list(buffered_reader: io.BufferedReader, target_list: list[str]):
    while True:
        line: bytes = buffered_reader.readline()
        if line in ("", b""):
            return
        target_list.append(line.decode("utf-8", errors="replace").rstrip())


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

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def start(self):
        self._proc = subprocess.Popen(args=self._args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self._thread_stdout = threading.Thread(
            target=_read_into_list, args=[self._proc.stdout, self._stdout], daemon=True
        )
        self._thread_stderr = threading.Thread(
            target=_read_into_list, args=[self._proc.stderr, self._stderr], daemon=True
        )
        self._thread_stdout.start()
        self._thread_stderr.start()
