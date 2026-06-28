"""Event-driven engine."""
import queue
import logging
from typing import Callable
from alphatrade.core.event import Event, EventType

logger = logging.getLogger(__name__)


class TradingEngine:
    """Central event loop — routes events to registered handlers."""

    def __init__(self):
        self._events: queue.Queue = queue.Queue()
        self._handlers: dict[EventType, list[Callable]] = {}
        self._running = False

    def register_handler(self, event_type: EventType, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def put(self, event: Event):
        self._events.put(event)

    def start(self):
        self._running = True
        logger.info("TradingEngine started.")
        while self._running:
            try:
                event = self._events.get(timeout=0.1)
                self._dispatch(event)
            except queue.Empty:
                continue

    def stop(self):
        self._running = False
        logger.info("TradingEngine stopped.")

    def _dispatch(self, event: Event):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed on {event}: {e}")
