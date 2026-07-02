"""
Complete event-driven backtesting engine.
"""

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

    Pipeline

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
       Virtual Execution
              │
              ▼
          Portfolio
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

        # Core components
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

        # Runtime state
        self._open_position: Optional[dict] = None
        self._trades: list[dict] = []
        self._equity_curve: list[dict] = []

        # Backtest settings
        self._capital = config["backtest"]["initial_capital"]
        self._commission = config["backtest"]["commission"]
        self._slippage = config["backtest"]["slippage"]

        # Register event handlers
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

    def run(self) -> dict:
        """
        Execute the complete historical backtest.
        """

        logger.info("Starting AlphaTrade Backtest...")

        # Subscribe to all enabled symbols
        for symbol in self._get_symbols():

            self.data_handler.subscribe(
                symbol,
                self.config["timeframes"]["primary"],
            )

        # Process historical bars
        for bar in self.data_handler.stream_bars():

            self.engine.put(bar)

            self._record_equity(
                bar.timestamp,
            )

        # Close any remaining open position
        if self._open_position:

            self._close_position(
                self._open_position["entry_price"],
                "END_OF_TEST",
            )

        logger.info("Calculating performance metrics...")

        metrics = PerformanceMetrics.calculate(
            self._trades,
            self._equity_curve,
            self.config["backtest"]["initial_capital"],
        )

        logger.info("Backtest completed successfully.")

        return metrics

    def _on_bar(self, event: BarEvent):
        """
        Called whenever a new historical bar arrives.
        """

        signal = self.strategy.on_bar(event)

        if signal is not None:
            self.engine.put(signal)

        if self._open_position is not None:
            self._manage_position(event)

    def _on_signal(self, event: SignalEvent):
        """
        Validate every signal using the Risk Manager.
        """

        if self._open_position is not None:
            return

        order = self.risk_manager.approve_signal(
            event,
            self._capital,
        )

        if order is not None:
            self.engine.put(order)

    def _on_order(self, event: OrderEvent):
        """
        Simulate order execution.
        """

        slippage = event.price * self._slippage

        if event.direction == "BUY":
            fill_price = event.price + slippage
        else:
            fill_price = event.price - slippage

        commission = (
            fill_price
            * event.quantity
            * self._commission
        )

        fill = FillEvent(
            symbol=event.symbol,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=f"BT_{datetime.utcnow().timestamp()}",
            stop_loss=event.stop_loss,
            take_profit=event.take_profit,
        )

        self.engine.put(fill)

    def _on_fill(self, event: FillEvent):
        """
        Store the executed trade.
        """

        self._open_position = {
            "symbol": event.symbol,
            "direction": event.direction,
            "quantity": event.quantity,
            "entry_price": event.fill_price,
            "stop_loss": event.stop_loss,
            "take_profit": event.take_profit,
            "commission": event.commission,
            "entry_time": event.timestamp,
        }

        self.risk_manager.record_fill(
            symbol=event.symbol,
            direction=event.direction,
            quantity=event.quantity,
            entry_price=event.fill_price,
            stop_loss=event.stop_loss,
            take_profit=event.take_profit,
        )

    def _manage_position(self, bar: BarEvent):
        """
        Monitor the open position for Stop Loss or Take Profit.
        """

        if self._open_position is None:
            return

        position = self._open_position

        if position["direction"] == "BUY":

            if bar.low <= position["stop_loss"]:

                self._close_position(
                    position["stop_loss"],
                    "STOP_LOSS",
                )

            elif bar.high >= position["take_profit"]:

                self._close_position(
                    position["take_profit"],
                    "TAKE_PROFIT",
                )

        else:

            if bar.high >= position["stop_loss"]:

                self._close_position(
                    position["stop_loss"],
                    "STOP_LOSS",
                )

            elif bar.low <= position["take_profit"]:

                self._close_position(
                    position["take_profit"],
                    "TAKE_PROFIT",
                )

    def _close_position(
        self,
        exit_price: float,
        reason: str,
    ):
        """
        Close the active position and record the trade.
        """

        if self._open_position is None:
            return

        position = self._open_position

        if position["direction"] == "BUY":

            gross_pnl = (
                exit_price
                - position["entry_price"]
            ) * position["quantity"]

        else:

            gross_pnl = (
                position["entry_price"]
                - exit_price
            ) * position["quantity"]

        net_pnl = (
            gross_pnl
            - position["commission"]
        )

        trade = {
            "symbol": position["symbol"],
            "direction": position["direction"],
            "entry_time": position["entry_time"],
            "exit_time": datetime.utcnow(),
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "quantity": position["quantity"],
            "gross_pnl": gross_pnl,
            "commission": position["commission"],
            "net_pnl": net_pnl,
            "reason": reason,
        }

        self._trades.append(trade)

        self._capital += net_pnl

        self.risk_manager.record_pnl(net_pnl)

        self.risk_manager.remove_position(
            position["symbol"]
        )

        self._open_position = None

    def _record_equity(
        self,
        timestamp: datetime,
    ):
        """
        Record account equity after each processed bar.
        """

        self._equity_curve.append(
            {
                "timestamp": timestamp,
                "equity": self._capital,
            }
        )

        self.drawdown.update(
            self._capital,
        )

    def _get_symbols(self) -> list[str]:
        """
        Return all enabled trading symbols from the configuration.
        """

        symbols = []

        for market, settings in self.config["markets"].items():

            if settings.get("enabled", False):

                symbols.extend(
                    settings.get(
                        "symbols",
                        [],
                    )
                )

        return symbols