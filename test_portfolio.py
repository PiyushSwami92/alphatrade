from datetime import datetime

from alphatrade.portfolio.portfolio import Portfolio
from alphatrade.core.event import FillEvent

portfolio = Portfolio(100000)

fill = FillEvent(
    symbol="EURUSD",
    direction="BUY",
    quantity=1.0,
    fill_price=1.1000,
    commission=2.0,
    order_id="TEST001",
    stop_loss=1.0950,
    take_profit=1.1100,
)

portfolio.update_fill(fill)

portfolio.close_position(
    exit_price=1.1050,
    exit_time=datetime.now(),
    reason="TP_HIT",
)

print("=" * 50)
print("Portfolio Test")
print("=" * 50)

print("Capital :", portfolio.capital)
print("Trades  :", portfolio.total_trades)
print("Equity  :", portfolio.equity)

print()
print(portfolio.closed_trades)