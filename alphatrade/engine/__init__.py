"""Backtesting and optimization engine."""

    def run(self) -> dict:
        """
        Execute the complete backtest.
        """

        logger.info("Starting backtest...")

        # Subscribe to all configured symbols
        for symbol in self._get_symbols():
            self.data_handler.subscribe(
                symbol,
                self.config["timeframes"]["primary"],
            )

        # Process historical bars
        for bar in self.data_handler.stream_bars():

            self.engine.put(bar)

            self._record_equity(bar.timestamp)

        # Close any remaining open position
        if self._open_position is not None:
            self._close_position(
                exit_price=self._open_position["entry_price"],
                reason="END_OF_TEST",
            )

        # Calculate performance metrics
        metrics = PerformanceMetrics.calculate(
            trades=self._trades,
            equity_curve=self._equity_curve,
            initial_capital=self.config["backtest"]["initial_capital"],
        )

        logger.info("Backtest completed successfully.")

        return metrics

    def _on_bar(self, event: BarEvent):
        """
        Handle a new market bar.
        """

        signal = self.strategy.on_bar(event)

        if signal is not None:
            self.engine.put(signal)

        if self._open_position is not None:
            self._manage_position(event)

    def _on_signal(self, event: SignalEvent):
        """
        Handle a trading signal.
        """

        # Allow only one position for now
        if self._open_position is not None:
            return

        order = self.risk_manager.approve_signal(
            signal=event,
            account_balance=self._capital,
        )

        if order is not None:
            self.engine.put(order)