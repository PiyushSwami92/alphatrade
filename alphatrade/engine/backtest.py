"""Complete event-driven backtesting engine."""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from alphatrade.core.engine import TradingEngine
from alphatrade.core.event import (
    BarEvent,
    EventType,
    FillEvent,
    OrderEvent,
    SignalEvent,
)
from alphatrade.data.historical import HistoricalDataHandler
from alphatrade.engine.metrics import PerformanceMetrics
from alphatrade.risk.drawdown import DrawdownTracker
from alphatrade.risk.manager import RiskManager
from alphatrade.strategies.base import Strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Complete event-driven backtesting engine.

    Pipeline:

        Historical Data
              │
              ▼
        Trading Engine
              │
              ▼
           Strategy
              │
              ▼
        Risk Manager
              │
              ▼
        Order Execution
              │
              ▼
        Portfolio Update
              │
              ▼
      Performance Metrics
    """

    def __init__(
        self,
        strategy: Strategy,
        config: dict,
    ):
        self.config = config
        self.strategy = strategy

        # Core Components
        self.engine = TradingEngine()

        self.data_handler = HistoricalDataHandler(
            config.get(
                "data_dir",
                "data/sample",
            )
        )

        self.risk_manager = RiskManager(
            config,
            config["backtest"]["initial_capital"],
        )

        self.drawdown = DrawdownTracker()

        # Runtime State
        self._open_position: Optional[dict] = None
        self._trades: list[dict] = []
        self._equity_curve: list[dict] = []

        # Backtest Settings
        self._capital = config["backtest"]["initial_capital"]
        self._commission = config["backtest"]["commission"]
        self._slippage = config["backtest"]["slippage"]

        # Register Event Handlers
        self.engine.register_handler(
            EventType.BAR,
            self._on_bar,
        )

        self.engine.register_handler(
            EventType.SIGNAL,
            self._on_signal,
        )

        self.engine.register_handler(
            EventType.ORDER,
            self._on_order,
        )

        self.engine.register_handler(
            EventType.FILL,
            self._on_fill,
        )