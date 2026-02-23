from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return record

    logging.setLogRecordFactory(record_factory)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s %(message)s",
        stream=sys.stdout,
    )


class TraceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "-"))
        return msg, kwargs


def get_logger(name: str, trace_id: str = "-") -> TraceLoggerAdapter:
    return TraceLoggerAdapter(logging.getLogger(name), {"trace_id": trace_id})
