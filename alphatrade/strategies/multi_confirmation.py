"""Multi-confirmation strategy — combines all signals before entering."""
import logging
from typing import Optional
import pandas as pd
from alphatrade.strategies.base import Strategy
from alphatrade.core.event import BarEvent, SignalEvent
from alphatrade.features.indicators import rsi, macd, atr, adx, supertrend, vwap, ema
from alphatrade.features.smc import (
    detect_swing_points, detect_bos, detect_cho_ch,
    detect_fvg, detect_order_blocks, detect_liquidity_sweeps,
)
from alphatrade.features.market_structure import detect_trend, detect_hh_hl
from alphatrade.features.candlestick_patterns import (
    detect_hammer, detect_shooting_star, detect_engulfing,
)
from alphatrade.features.supply_demand import detect_zones, is_near_zone

logger = logging.getLogger(__name__)


class MultiConfirmationStrategy(Strategy):
    """
    Enters only when multiple confirmations align.
    Uses 18 confirmation sources for high-quality trade filtering.
    """

    def __init__(self, params: dict, min_confirmations: int = 4):
        self.params = params
        self.min_confirmations = min_confirmations
        self._bars: dict[str, pd.DataFrame] = {}

    def on_bar(self, bar: BarEvent) -> Optional[SignalEvent]:
        symbol = bar.symbol
        if symbol not in self._bars:
            self._bars[symbol] = pd.DataFrame(columns=[
                "timestamp", "open", "high", "low", "close", "volume"
            ])

        new_row = {
            "timestamp": bar.timestamp, "open": bar.open, "high": bar.high,
            "low": bar.low, "close": bar.close, "volume": bar.volume,
        }
        self._bars[symbol] = pd.concat([
            self._bars[symbol], pd.DataFrame([new_row])
        ], ignore_index=True)

        df = self._bars[symbol]
        if len(df) < 50:
            return None

        ind = self._compute_indicators(df)
        return self._evaluate_setup(symbol, df, ind)

    def _compute_indicators(self, df: pd.DataFrame) -> dict:
        close = df["close"]
        p = self.params
        return {
            "rsi": rsi(close, p.get("rsi_period", 14)).iloc[-1],
            "macd_line": macd(close, p.get("macd_fast", 12), p.get("macd_slow", 26), p.get("macd_signal", 9))[0].iloc[-1],
            "macd_signal": macd(close, p.get("macd_fast", 12), p.get("macd_slow", 26), p.get("macd_signal", 9))[1].iloc[-1],
            "macd_histogram": macd(close, p.get("macd_fast", 12), p.get("macd_slow", 26), p.get("macd_signal", 9))[2].iloc[-1],
            "ema_9": ema(close, 9).iloc[-1],
            "ema_21": ema(close, 21).iloc[-1],
            "ema_50": ema(close, 50).iloc[-1],
            "ema_200": ema(close, 200).iloc[-1] if len(df) >= 200 else None,
            "atr": atr(df, p.get("atr_period", 14)).iloc[-1],
            "adx": adx(df, p.get("adx_period", 14)).iloc[-1],
            "supertrend": supertrend(df, p.get("supertrend_period", 10), p.get("supertrend_multiplier", 3.0))[1].iloc[-1],
            "vwap": vwap(df).iloc[-1],
            "market_structure": detect_swing_points(df),
            "bos": detect_bos(df, detect_swing_points(df)),
            "cho_ch": detect_cho_ch(df, detect_swing_points(df)),
            "hh_hl": detect_hh_hl(df),
            "trend": detect_trend(df),
            "fvg": detect_fvg(df),
            "order_blocks": detect_order_blocks(df),
            "liquidity_sweeps": detect_liquidity_sweeps(df),
            "supply_demand": detect_zones(df),
            "hammer": detect_hammer(df).iloc[-1],
            "shooting_star": detect_shooting_star(df).iloc[-1],
            "engulfing": detect_engulfing(df).iloc[-1],
        }

    def _evaluate_setup(self, symbol: str, df: pd.DataFrame, ind: dict) -> Optional[SignalEvent]:
        confirmations_buy = []
        confirmations_sell = []
        close_price = df["close"].iloc[-1]
        atr_val = ind["atr"]
        p = self.params

        if pd.isna(atr_val) or atr_val == 0:
            return None

        # Trend
        if ind["trend"] == "UPTREND":
            confirmations_buy.append("uptrend")
        elif ind["trend"] == "DOWNTREND":
            confirmations_sell.append("downtrend")

        # Market structure
        if ind["hh_hl"]["higher_highs"] and ind["hh_hl"]["higher_lows"]:
            confirmations_buy.append("hh_hl")
        if ind["hh_hl"]["lower_highs"] and ind["hh_hl"]["lower_lows"]:
            confirmations_sell.append("lh_ll")

        # BOS / CHOCH
        if ind["bos"] == "BOS_BULLISH":
            confirmations_buy.append("bos_bullish")
        elif ind["bos"] == "BOS_BEARISH":
            confirmations_sell.append("bos_bearish")
        if ind["cho_ch"] == "CHOCH_BULLISH":
            confirmations_buy.append("cho_ch_bullish")
        elif ind["cho_ch"] == "CHOCH_BEARISH":
            confirmations_sell.append("cho_ch_bearish")

        # EMA alignment
        if ind["ema_9"] > ind["ema_21"] > ind["ema_50"]:
            confirmations_buy.append("ema_bullish")
        elif ind["ema_9"] < ind["ema_21"] < ind["ema_50"]:
            confirmations_sell.append("ema_bearish")

        # RSI
        if ind["rsi"] < p.get("rsi_oversold", 30):
            confirmations_buy.append("rsi_oversold")
        elif ind["rsi"] > p.get("rsi_overbought", 70):
            confirmations_sell.append("rsi_overbought")

        # MACD
        if ind["macd_histogram"] > 0 and ind["macd_line"] > ind["macd_signal"]:
            confirmations_buy.append("macd_bullish")
        elif ind["macd_histogram"] < 0 and ind["macd_line"] < ind["macd_signal"]:
            confirmations_sell.append("macd_bearish")

        # Supertrend
        if ind["supertrend"] == 1:
            confirmations_buy.append("supertrend_up")
        elif ind["supertrend"] == -1:
            confirmations_sell.append("supertrend_down")

        # ADX
        if ind["adx"] > p.get("adx_threshold", 25):
            if ind["trend"] == "UPTREND":
                confirmations_buy.append("adx_strong")
            elif ind["trend"] == "DOWNTREND":
                confirmations_sell.append("adx_strong")

        # VWAP
        if close_price > ind["vwap"]:
            confirmations_buy.append("vwap_above")
        else:
            confirmations_sell.append("vwap_below")

        # FVG
        for fvg in ind["fvg"]:
            if fvg["index"] >= len(df) - 5:
                if fvg["type"] == "BULLISH_FVG" and fvg["top"] >= close_price >= fvg["bottom"]:
                    confirmations_buy.append("fvg_bullish")
                if fvg["type"] == "BEARISH_FVG" and fvg["top"] >= close_price >= fvg["bottom"]:
                    confirmations_sell.append("fvg_bearish")

        # Order Blocks
        for ob in ind["order_blocks"]:
            if ob["index"] >= len(df) - 10:
                if ob["type"] == "BULLISH_OB" and ob["top"] >= close_price >= ob["low"]:
                    confirmations_buy.append("order_block_bullish")
                if ob["type"] == "BEARISH_OB" and ob["high"] >= close_price >= ob["low"]:
                    confirmations_sell.append("order_block_bearish")

        # Liquidity Sweeps
        for s in ind["liquidity_sweeps"]:
            if s["index"] >= len(df) - 5:
                if s["type"] == "LIQUIDITY_SWEEP_BULLISH":
                    confirmations_buy.append("liq_sweep_bullish")
                if s["type"] == "LIQUIDITY_SWEEP_BEARISH":
                    confirmations_sell.append("liq_sweep_bearish")

        # Candlestick Patterns
        if ind["hammer"]:
            confirmations_buy.append("hammer")
        if ind["shooting_star"]:
            confirmations_sell.append("shooting_star")
        if ind["engulfing"] == "BULLISH_ENGULFING":
            confirmations_buy.append("bullish_engulfing")
        elif ind["engulfing"] == "BEARISH_ENGULFING":
            confirmations_sell.append("bearish_engulfing")

        # Supply & Demand Zones
        if is_near_zone(close_price, ind["supply_demand"]["demand"]):
            confirmations_buy.append("demand_zone")
        if is_near_zone(close_price, ind["supply_demand"]["supply"]):
            confirmations_sell.append("supply_zone")

        # Decision
        buy_count = len(confirmations_buy)
        sell_count = len(confirmations_sell)

        if buy_count >= self.min_confirmations and buy_count > sell_count:
            sl = close_price - p.get("atr_multiplier_sl", 1.5) * atr_val
            tp = close_price + p.get("atr_multiplier_tp", 3.0) * atr_val
            strength = min(buy_count / (buy_count + sell_count + 1), 1.0)
            return SignalEvent(
                symbol=symbol, direction="BUY", strength=strength,
                entry_price=close_price, stop_loss=sl, take_profit=tp,
                reason={"confirmations": confirmations_buy, "total": buy_count},
            )

        elif sell_count >= self.min_confirmations and sell_count > buy_count:
            sl = close_price + p.get("atr_multiplier_sl", 1.5) * atr_val
            tp = close_price - p.get("atr_multiplier_tp", 3.0) * atr_val
            strength = min(sell_count / (buy_count + sell_count + 1), 1.0)
            return SignalEvent(
                symbol=symbol, direction="SELL", strength=strength,
                entry_price=close_price, stop_loss=sl, take_profit=tp,
                reason={"confirmations": confirmations_sell, "total": sell_count},
            )

        return None
