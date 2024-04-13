import json
import pprint


class LazyToStr:
    def __init__(self, instance: object):
        self._instance = instance

    def __str__(self):
        try:
            return json.dumps(self._instance, sort_keys=True, indent=4)
        except TypeError:
            return pprint.pformat(self._instance, indent=4)
