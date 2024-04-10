import json
import pathlib

IGNORED_ENVS = [".pkg"]


def main():
    result = json.loads(pathlib.Path("./tox-result.json").read_text())
    for env_name in sorted([_ for _ in result["testenvs"].keys() if _ not in IGNORED_ENVS]):
        env = result["testenvs"][env_name]
        assert env["result"]["success"]
        # ![Static Badge](https://img.shields.io/badge/py3.11%2Bpg12-pass-green)
        badge_label = env_name.replace("-", "%2B")
        badge = f"![Static Badge](https://img.shields.io/badge/{badge_label}-pass-green)"
        print(badge)


if __name__ == "__main__":
    main()
