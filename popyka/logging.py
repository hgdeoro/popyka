import json


class LazyJson:
    def __init__(self, instance: object):
        self._instance = instance

    def __str__(self):
        # FIXME: Implement fallback mechanism like pprint.pformat()
        return json.dumps(self._instance, sort_keys=True, indent=4)
