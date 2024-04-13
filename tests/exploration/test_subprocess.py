import time

from tests.subp_collector import SubProcCollector


def test():
    sp = SubProcCollector(args=["vmstat", "1", "3"])
    sp.start()
    while True:
        print(f"STDOUT: {len(sp.stdout)}")
        print(f"STDERR: {len(sp.stderr)}")
        time.sleep(1)
