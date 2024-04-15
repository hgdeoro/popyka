import json
import os
import pprint


class LazyToStr:
    def __init__(self, instance: object):
        self._instance = instance
        self._compact = bool(os.environ.get("LAZYTOSTR_COMPACT", "0") == "1")

    def __str__(self):
        try:
            if self._compact:
                return json.dumps(self._instance, sort_keys=True)
            else:
                return json.dumps(self._instance, sort_keys=True, indent=4)
        except TypeError:
            return pprint.pformat(self._instance, indent=4)
