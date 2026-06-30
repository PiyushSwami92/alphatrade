"""Professional risk management — capital preservation first."""
import logging
from datetime import date
from typing import Optional
from alphatrade.core.event import SignalEvent, OrderEvent
from alphatrade.risk.position_sizing import calculate_position_size

logger = logging.getLogger(__name__)


class RiskManager:
    """Enforces all risk rules: 1% rule, daily/weekly limits, drawdown, R:R."""

    def __init__(self, config: dict, initial_balance: float = 100_000.0):
        self.config = config["risk"]
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self._daily_pnl: dict[date, float] = {}
        self._weekly_pnl: dict[int, float] = {}
        self._open_positions: list[dict] = []

    def approve_signal(self, signal: SignalEvent, account_balance: float) -> Optional[OrderEvent]:
        today = date.today()
        week = today.isocalendar()[1]

        # Daily loss limit
        daily_loss = self._daily_pnl.get(today, 0.0)
        max_daily_loss = -abs(self.config["max_daily_loss"]) * self.initial_balance
        if daily_loss <= max_daily_loss:
            logger.warning(f"Daily loss limit hit ({daily_loss:.2f}). Skipping.")
            return None

        # Weekly loss limit
        weekly_loss = self._weekly_pnl.get(week, 0.0)
        max_weekly_loss = -abs(self.config["max_weekly_loss"]) * self.initial_balance
        if weekly_loss <= max_weekly_loss:
            logger.warning(f"Weekly loss limit hit ({weekly_loss:.2f}). Skipping.")
            return None

        # Max drawdown
        current_dd = (self.peak_balance - account_balance) / self.peak_balance
        if current_dd >= self.config["max_drawdown"]:
            logger.warning(f"Max drawdown ({current_dd:.2%}) reached. Stopping.")
            return None

        # Max open positions
        if len(self._open_positions) >= self.config.get("max_open_positions", 5):
            logger.info("Max open positions reached.")
            return None

        # R:R check
        if signal.direction == "BUY":
            risk = signal.entry_price - signal.stop_loss
            reward = signal.take_profit - signal.entry_price
        else:
            risk = signal.stop_loss - signal.entry_price
            reward = signal.entry_price - signal.take_profit

        if risk <= 0:
            logger.warning(f"Invalid risk ({risk}).")
            return None

        rr = reward / risk
        if rr < self.config.get("min_rr_ratio", 2.0):
            logger.info(f"R:R {rr:.2f} < minimum. Skipping.")
            return None

        # Position size (1% risk)
        max_risk_amount = account_balance * self.config["max_risk_per_trade"]
        quantity = calculate_position_size(max_risk_amount, risk, signal.entry_price)

        if quantity <= 0:
            logger.warning("Quantity <= 0. Skipping.")
            return None

        logger.info(
            f"APPROVED | {signal.direction} {signal.symbol} | "
            f"Qty: {quantity:.4f} | SL: {signal.stop_loss:.4f} | "
            f"TP: {signal.take_profit:.4f} | R:R: {rr:.2f}"
        )

        return OrderEvent(
            symbol=signal.symbol,
            direction=signal.direction,
            order_type="MARKET",
            quantity=quantity,
            price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

    def record_fill(
    self,
    symbol: str,
    direction: str,
    quantity: float,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
):
    self._open_positions.append(
        {
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
    )

    def record_pnl(self, pnl: float):
        self.current_balance += pnl
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        today = date.today()
        week = today.isocalendar()[1]
        self._daily_pnl[today] = self._daily_pnl.get(today, 0.0) + pnl
        self._weekly_pnl[week] = self._weekly_pnl.get(week, 0.0) + pnl

    def remove_position(self, symbol: str):
        self._open_positions = [p for p in self._open_positions if p.get("symbol") != symbol]
