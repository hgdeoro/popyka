import json
import pathlib
import re
import unittest

IGNORED_ENVS = [".pkg"]
BADGE_LABEL_RE = re.compile(r"py3(\d+)-pg(\d+)")


def format_badge_label(env_name: str):
    match = BADGE_LABEL_RE.fullmatch(env_name)
    assert match
    python_minor_version = match.group(1)
    postgres_major_version = match.group(2)
    return f"py3.{python_minor_version}%2Bpg{postgres_major_version}"


def main():
    result = json.loads(pathlib.Path("./tox-result.json").read_text())
    for env_name in sorted([_ for _ in result["testenvs"].keys() if _ not in IGNORED_ENVS]):
        env = result["testenvs"][env_name]
        assert env["result"]["success"]
        # ![Static Badge](https://img.shields.io/badge/py3.11%2Bpg12-pass-green)
        badge_label = format_badge_label(env_name)
        badge = f"![{env_name}](https://img.shields.io/badge/{badge_label}-passed-green)"
        print(badge)


if __name__ == "__main__":
    main()


class TestFormatBadgeLabel(unittest.TestCase):
    def test(self):
        label = format_badge_label("py310-pg12")
        self.assertEquals(label, "py3.10%2Bpg12")
