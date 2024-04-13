import time

from tests.conftest import slow_test
from tests.subp_collector import SubProcCollector


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
