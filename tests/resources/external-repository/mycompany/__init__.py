import json
import logging

from popyka.api import Processor, Wal2JsonV2Change


class MyCompanyCustomProcessor(Processor):
    logger = logging.getLogger(f"{__name__}.MyCompanyCustomProcessor")

    def setup(self):
        pass

    def process_change(self, change: Wal2JsonV2Change):
        self.logger.info("MyCompanyCustomProcessor-received-a-change####%s####", json.dumps(change, sort_keys=True))
