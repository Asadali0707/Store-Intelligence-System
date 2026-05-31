"""
events/emitter.py — Structured event writer to Redis Streams
"""
import redis
import json
import uuid
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class StoreEvent:
    event_type: str          # ENTRY | EXIT | REENTRY | DWELL
    track_id: int
    timestamp: str           # ISO 8601
    zone: str
    confidence: float
    camera_id: str
    store_id: str
    is_staff: bool = False
    group_id: Optional[str] = None
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self.event_id = f"evt_{ts}_{self.track_id:04d}_{uuid.uuid4().hex[:4]}"


class EventEmitter:
    """
    Writes store events to Redis Streams.
    Stream key: store:{store_id}:events
    Consumer groups allow multiple downstream consumers (aggregator, anomaly detector).
    """

    STREAM_MAXLEN = 100_000  # ~1 month of events at peak retail traffic

    def __init__(self, redis_url: str, store_id: str):
        self.r = redis.from_url(redis_url, decode_responses=True)
        self.store_id = store_id
        self.stream_key = f"store:{store_id}:events"
        self._ensure_consumer_group()

    def _ensure_consumer_group(self):
        try:
            self.r.xgroup_create(self.stream_key, "aggregator", id="0", mkstream=True)
        except redis.exceptions.ResponseError:
            pass  # group already exists

    def emit(self, event: StoreEvent) -> str:
        """Write event to Redis Stream. Returns stream entry ID."""
        data = {k: str(v) for k, v in asdict(event).items()}
        entry_id = self.r.xadd(
            self.stream_key,
            data,
            maxlen=self.STREAM_MAXLEN,
            approximate=True,
        )
        return entry_id

    def emit_entry(self, track_id: int, zone: str, conf: float,
                   camera_id: str, is_staff: bool = False, group_id: str = None) -> str:
        event = StoreEvent(
            event_type="ENTRY",
            track_id=track_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            zone=zone,
            confidence=conf,
            camera_id=camera_id,
            store_id=self.store_id,
            is_staff=is_staff,
            group_id=group_id,
        )
        return self.emit(event)

    def emit_exit(self, track_id: int, zone: str, conf: float, camera_id: str) -> str:
        event = StoreEvent(
            event_type="EXIT",
            track_id=track_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            zone=zone,
            confidence=conf,
            camera_id=camera_id,
            store_id=self.store_id,
        )
        return self.emit(event)

    def emit_reentry(self, track_id: int, zone: str, conf: float, camera_id: str) -> str:
        event = StoreEvent(
            event_type="REENTRY",
            track_id=track_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            zone=zone,
            confidence=conf,
            camera_id=camera_id,
            store_id=self.store_id,
        )
        return self.emit(event)

    def get_recent(self, count: int = 50):
        entries = self.r.xrevrange(self.stream_key, count=count)
        return [{"id": e[0], **e[1]} for e in entries]
