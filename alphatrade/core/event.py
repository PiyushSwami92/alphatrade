"""Event system for event-driven trading architecture."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class EventType(Enum):
    """All event types flowing through the system."""
    TICK = auto()
    BAR = auto()
    SIGNAL = auto()
    ORDER = auto()
    FILL = auto()
    CANCEL = auto()
    REJECT = auto()
    ACCOUNT_UPDATE = auto()
    RISK_WARNING = auto()
    SHUTDOWN = auto()


@dataclass(kw_only=True)
class Event:
    """Base class for all events."""

    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TickEvent(Event):
    symbol: str
    bid: float
    ask: float
    volume: float

    event_type = EventType.TICK


@dataclass
class BarEvent(Event):
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    event_type = EventType.BAR


@dataclass
class SignalEvent(Event):
    symbol: str
    direction: str
    strength: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: dict

    event_type = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    symbol: str
    direction: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_id: Optional[str] = None

    event_type = EventType.ORDER


@dataclass
class FillEvent(Event):
    symbol: str
    direction: str
    quantity: float
    fill_price: float
    commission: float
    order_id: str

    event_type = EventType.FILL