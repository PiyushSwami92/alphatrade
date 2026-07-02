"""Portfolio tracker — manages positions, P&L, and account state."""

import logging
from datetime import datetime
from typing import Optional

from alphatrade.core.event import FillEvent

logger = logging.getLogger(__name__)


class Portfolio:
    """Tracks open positions, closed trades, and account balance."""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: list[dict] = []
        self.closed_trades: list[dict] = []
        self._open_position: Optional[dict] = None

    def update_fill(self, fill: FillEvent):
        """Record a fill as an open position."""

        self._open_position = {
            "symbol": fill.symbol,
            "direction": fill.direction,
            "quantity": fill.quantity,
            "entry_price": fill.fill_price,
            "entry_time": fill.timestamp,
            "commission": fill.commission,
        }

        logger.info(
            f"Position opened: {fill.direction} "
            f"{fill.quantity} {fill.symbol} @ {fill.fill_price}"
        )

    def close_position(
        self,
        exit_price: float,
        exit_time: datetime,
        reason: str,
    ):
        """Close the current position and record the trade."""

        if self._open_position is None:
            return

        pos = self._open_position

        contract_size = 100000

        if pos["direction"] == "BUY":
            gross_pnl = (
                (exit_price - pos["entry_price"])
                * contract_size
                * pos["quantity"]
            )
        else:
            gross_pnl = (
                (pos["entry_price"] - exit_price)
                * contract_size
                * pos["quantity"]
            )

        net_pnl = gross_pnl - pos["commission"]

        trade = {
            **pos,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "reason": reason,
        }

        self.closed_trades.append(trade)
        self.capital += net_pnl

        logger.info(
            f"Position closed: "
            f"{pos['direction']} "
            f"{pos['symbol']} "
            f"| PnL: {net_pnl:.2f}"
        )

        self._open_position = None

    @property
    def open_position(self) -> Optional[dict]:
        return self._open_position

    @property
    def total_trades(self) -> int:
        return len(self.closed_trades)

    @property
    def equity(self) -> float:
        return self.capital