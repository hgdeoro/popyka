import json
import logging

import psycopg2.extras

logger = logging.getLogger(__name__)


class ConsumerStatsToLog:
    """Logs the size of the payload received"""

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        logger.info("ConsumerStatsToLog: received payload size: %s", len(msg.payload))
        msg.cursor.send_feedback(flush_lsn=msg.data_start)


class ConsumerDumpToLog:
    """Parses the payload (assuming JSON) and logs a formatted version"""

    def __call__(self, msg: psycopg2.extras.ReplicationMessage):
        payload = json.dumps(json.loads(msg.payload), indent=4, sort_keys=True)
        logger.info("ConsumerDumpToLog: received payload: %s", payload)
        msg.cursor.send_feedback(flush_lsn=msg.data_start)
