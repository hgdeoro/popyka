import json
import logging

import psycopg2.extras

from popyka.api import Filter, Processor, Wal2JsonV2Change
from popyka.errors import PopykaException
from popyka.logging import LazyToStr


class ReplicationConsumerToProcessorAdaptor:
    """Psycopg2 replication consumer that runs configured PoPyKa Processors on the received changes"""

    logger = logging.getLogger(f"{__name__}.ReplicationConsumerToProcessorAdaptor")

    def __init__(self, processors: list[Processor], filters: list[Filter]):
        self._processors = processors
        self._filters = filters

    def _handle_payload(self, payload: bytes):
        change = Wal2JsonV2Change(json.loads(payload))
        process_change = True

        for a_filter in self._filters:
            match a_filter.filter(change):
                case Filter.Result.IGNORE:
                    self.logger.debug("Ignoring change for change: %s", LazyToStr(change))
                    return  # ignore this message
                case Filter.Result.PROCESS:
                    break  # stop filtering
                case Filter.Result.CONTINUE:
                    continue  # continue, evaluate other filters
                case _:
                    raise PopykaException("Filter.filter() returned invalid value")

        if process_change:
            for processor in self._processors:
                self.logger.debug("Starting processing with processor: %s", processor)
                processor.process_change(change)

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        self.logger.debug("ReplicationConsumerToProcessorAdaptor: received payload: %s", msg)

        # Handle the payload
        self._handle_payload(msg.payload)

        # Flush after every message is successfully processed
        self.logger.debug("send_feedback() flush_lsn=%s", msg.data_start)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)
