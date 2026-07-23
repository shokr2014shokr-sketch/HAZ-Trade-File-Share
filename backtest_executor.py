# ==========================================================
# HAZ TRADE
# UNIVERSAL BACKTEST EXECUTOR
# FILTER-AWARE EXECUTION ENGINE
# VERSION : V10.02
# ==========================================================
import math
import numpy as np

class BacktestExecutor:
    # =====================================================
    # INITIALIZATION
    # =====================================================
    def __init__(self, backtest_engine, trade_manager, risk_percent, rr, log):
        self.backtest_engine = backtest_engine
        self.trade_manager = trade_manager
        self.risk_percent = risk_percent
        self.rr = rr
        self.log = log
        self.total_received = 0
        self.total_executed = 0
        self.total_rejected = 0
        self.total_ignored = 0
        self.total_invalid = 0
        self.total_open_failed = 0
        self.total_wins = 0
        self.total_losses = 0
        self.total_still_open = 0
        self.total_exit_signals = 0

    # =====================================================
    # STANDARD EXECUTION RESULT
    # =====================================================
    @staticmethod
    def _result(balance, win=False, loss=False, executed=False, rejected=False, ignored=False, status="NO_ACTION", reason=None, signal=None, trade=None, profit=0.0):
        return {"balance": float(balance), "win": bool(win), "loss": bool(loss), "executed": bool(executed), "rejected": bool(rejected), "ignored": bool(ignored), "status": str(status), "reason": reason, "profit": float(profit), "signal": signal, "trade": trade}

    # =====================================================
    # NUMBER VALIDATION
    # =====================================================
    @staticmethod
    def _is_valid_number(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(value)

    # =====================================================
    # ENGINE DATA ACCESS
    # =====================================================
    @staticmethod
    def _get_engine_array(engine, *names):
        for name in names:
            if isinstance(engine, dict):
                value = engine.get(name)
                if value is not None:
                    return value
            value = getattr(engine, name, None)
            if value is not None:
                return value
        return None

    @classmethod
    def _get_index_value(cls, engine, index, *names):
        values = cls._get_engine_array(engine, *names)
        if values is None:
            return None
        try:
            return values[index]
        except (IndexError, KeyError, TypeError):
            return None

    # =====================================================
    # TRADE DATA ACCESS
    # =====================================================
    @staticmethod
    def _get_trade_value(trade, key, default=None):
        if trade is None:
            return default
        return trade.get(key, default) if isinstance(trade, dict) else getattr(trade, key, default)

    @staticmethod
    def _set_trade_value(trade, key, value):
        if trade is None: return
        if isinstance(trade, dict): trade[key] = value
        else: setattr(trade, key, value)

    # =====================================================
    # SIGNAL NORMALIZATION
    # =====================================================
    @staticmethod
    def _get_execution(signal):
        if not isinstance(signal, dict):
            return ""
        return str(signal.get("execution", "")).strip().upper()

    @staticmethod
    def _get_event(signal):
        if not isinstance(signal, dict):
            return ""
        return str(signal.get("event", "")).strip().upper()

    @staticmethod
    def _is_rejected_signal(signal):
        if not isinstance(signal, dict):
            return False
        return bool(signal.get("rejected", False)) or signal.get("accepted") is False or signal.get("filter_passed") is False or signal.get("final_quality_passed") is False

    @classmethod
    def _is_exit_signal(cls, signal):
        execution, event = cls._get_execution(signal), cls._get_event(signal)
        return any(keyword in execution or keyword in event for keyword in ("EXIT", "CLOSE", "FLAT"))

    @staticmethod
    def _is_event_driven_strategy(signal): return str(signal.get("strategy", "")).strip().lower().startswith("swordstrategy")

    # =====================================================
    # SIGNAL DIRECTION MAPPING
    # =====================================================
    @classmethod
    def _map_exit_direction(cls, signal):
        execution, event = cls._get_execution(signal), cls._get_event(signal)
        if "EXIT_LONG" in execution or "LONG_EXIT" in event:
            return "LONG"
        if "EXIT_SHORT" in execution or "SHORT_EXIT" in event:
            return "SHORT"
        return None

    @classmethod
    def _map_direction(cls, signal):
        execution = cls._get_execution(signal)
        if execution in ("OPEN_LONG", "REVERSE_LONG", "ADD_LONG", "BUY"):
            return "LONG"
        if execution in ("OPEN_SHORT", "REVERSE_SHORT", "ADD_SHORT", "SELL"):
            return "SHORT"
        return None

    @classmethod
    def _get_entry_type(cls, signal):
        execution, event = cls._get_execution(signal), cls._get_event(signal)
        if "ADD" in execution or "ADDON" in event:
            return "ADDON"
        if "REVERSE" in execution:
            return "REVERSE"
        if "MOTHER" in event:
            return "MOTHER"
        return "PRIMARY"

    # =====================================================
    # SIGNAL METADATA ATTACHMENT
    # =====================================================
    def _attach_signal_metadata(self, trade, signal, direction, index):
        original_features = signal.get("features", {})
        if not isinstance(original_features, dict): original_features = {}
        features = dict(original_features)
        features.update({
            "strategy": signal.get("strategy", ""), "strategy_class": signal.get("strategy_class", ""), "event": signal.get("event", ""),
            "execution": signal.get("execution", ""), "raw_execution": signal.get("raw_execution", signal.get("execution", "")),
            "direction": signal.get("direction") or direction, "entry_type": self._get_entry_type(signal), "signal_index": index, "entry_index": index,
            "quality_score": signal.get("score", 0), "quality_class": signal.get("quality_class", ""), "score_passed": signal.get("score_passed", False),
            "filter_passed": signal.get("filter_passed", False), "direction_quality_ok": signal.get("direction_quality_ok", False),
            "final_quality_passed": signal.get("final_quality_passed", False), "acceptance_reason": signal.get("acceptance_reason", ""),
            "rejection_reasons": signal.get("rejection_reasons", []), "score_details": signal.get("score_details", {}), "filter_result": signal.get("filter_result", {}),
            "mother": bool(signal.get("mother", signal.get("event") in ("SHORT_MOTHER", "LONG_MOTHER"))),
            "addon": bool(signal.get("addon", signal.get("event") in ("SHORT_ADDON", "LONG_ADDON"))),
            "trend_ok": bool(signal.get("trend_ok", False)), "ema_ok": bool(signal.get("ema_ok", False)),
            "lux_strength": float(signal.get("lux_strength", signal.get("lux_range", 0.0)) or 0.0),
            "lux_range": float(signal.get("lux_range", signal.get("lux_strength", 0.0)) or 0.0),
            "htf_router_ready": bool(signal.get("htf_router_ready", False)), "htf_long_allowed": bool(signal.get("htf_long_allowed", False)),
            "htf_short_allowed": bool(signal.get("htf_short_allowed", False)), "liquidity_sweep": bool(signal.get("liquidity_sweep", False)),
            "confirmation": bool(signal.get("confirmation", False)),
        })
        self._set_trade_value(trade, "features", features)
        self._set_trade_value(trade, "signal", dict(signal))
        self._set_trade_value(trade, "strategy", signal.get("strategy", ""))
        self._set_trade_value(trade, "signal_score", signal.get("score", 0))
        self._set_trade_value(trade, "quality_class", signal.get("quality_class", ""))
        self._set_trade_value(trade, "entry_type", self._get_entry_type(signal))
        for key in ("mother", "addon", "trend_ok", "ema_ok", "lux_strength", "lux_range", "htf_router_ready", "htf_long_allowed", "htf_short_allowed"):
            self._set_trade_value(trade, key, features.get(key))
        return trade

    # =====================================================
    # CLOSED TRADE METADATA
    # =====================================================
    def _update_closed_trade_features(self, trade, result, profit, balance_before, exit_reason, exit_price, exit_index, exit_time):
        features = self._get_trade_value(trade, "features", {})
        if not isinstance(features, dict): features = {}
        features = dict(features)
        features.update({"result": result, "profit": float(profit), "return_percent": float(profit) / float(balance_before) * 100.0 if balance_before > 0.0 else 0.0, "exit_reason": exit_reason, "exit_price": float(exit_price), "exit_index": int(exit_index), "exit_time": exit_time})
        self._set_trade_value(trade, "features", features)
        return trade

    # =====================================================
    # BACKTEST LOGGING
    # =====================================================
    def _append_log(self, trade, entry_time, exit_time, signal):
        if self.log is None: return
        self.log.append([entry_time, exit_time, self._get_trade_value(trade, "direction", ""), self._get_trade_value(trade, "entry", 0.0), self._get_trade_value(trade, "stop_loss", 0.0), self._get_trade_value(trade, "take_profit", 0.0), self._get_trade_value(trade, "profit", 0.0), signal.get("strategy", ""), signal.get("event", ""), self._get_entry_type(signal), signal.get("score", 0), signal.get("quality_class", "")])

    # =====================================================
    # ACTIVE POSITION STATE
    # =====================================================
    def _get_open_positions(self):
        positions = getattr(
            self.trade_manager,
            "open_positions",
            None,
        )

        if positions is None:
            getter = getattr(
                self.trade_manager,
                "get_open_positions",
                None,
            )

            if callable(getter):
                positions = getter()

        if positions is None:
            return []

        if isinstance(positions, dict):
            return list(positions.values())

        try:
            return list(positions)
        except TypeError:
            return []

    def _get_position_state(self):
        has_long_position = False
        has_short_position = False

        for trade in self._get_open_positions():
            direction = str(
                self._get_trade_value(
                    trade,
                    "direction",
                    "",
                )
            ).strip().upper()

            if direction in ("LONG", "BUY"):
                has_long_position = True

            elif direction in ("SHORT", "SELL"):
                has_short_position = True

        return has_long_position, has_short_position

    # =====================================================
    # SIGNAL ENGINE ACCESS
    # =====================================================
    def _get_signal_engine(self):
        return getattr(
            self.backtest_engine,
            "signal_engine",
            None,
        )

    # =====================================================
    # STRATEGY STATE SYNCHRONIZATION
    # =====================================================
    def _synchronize_strategy_state(self):
        signal_engine = self._get_signal_engine()

        if signal_engine is None:
            return False

        synchronize = getattr(
            signal_engine,
            "synchronize_position_state",
            None,
        )

        if not callable(synchronize):
            return False

        has_long_position, has_short_position = (
            self._get_position_state()
        )

        return bool(
            synchronize(
                has_long_position=has_long_position,
                has_short_position=has_short_position,
            )
        )

    # =====================================================
    # STRATEGY EXECUTION CONFIRMATION
    # =====================================================
    def _confirm_strategy_execution(
        self,
        execution,
        success,
    ):
        signal_engine = self._get_signal_engine()

        if signal_engine is None:
            return False

        confirm = getattr(
            signal_engine,
            "confirm_execution",
            None,
        )

        if not callable(confirm):
            return False

        return bool(
            confirm(
                execution=execution,
                success=success,
            )
        )

    # =====================================================
    # EXECUTION SUCCESS VALIDATION
    # =====================================================
    @staticmethod
    def _execution_succeeded(result):
        if not isinstance(result, dict):
            return False

        if result.get("rejected") or result.get("ignored"):
            return False

        if not result.get("executed"):
            return False

        status = str(
            result.get(
                "status",
                "",
            )
        ).strip().upper()

        failure_keywords = (
            "FAILED",
            "INVALID",
            "REJECTED",
            "MISSING",
            "UNKNOWN",
            "NO_MATCHING",
        )

        return not any(
            keyword in status
            for keyword in failure_keywords
        )

    # =====================================================
    # EXECUTION ENGINE
    # =====================================================
    def execute(
        self,
        signal,
        index,
        engine,
        balance,
    ):
        self._synchronize_strategy_state()

        result = self._execute_core(
            signal=signal,
            index=index,
            engine=engine,
            balance=balance,
        )

        execution = self._get_execution(signal)
        success = self._execution_succeeded(result)

        if execution not in (
            "",
            "NONE",
            "NO_ACTION",
            "NO_SIGNAL",
            "HOLD",
            "WAIT",
        ):
            self._confirm_strategy_execution(
                execution=execution,
                success=success,
            )

        self._synchronize_strategy_state()

        return result

    def _execute_core(self, signal, index, engine, balance):
        self.total_received += 1
        print("=" * 60)
        print("BACKTEST EXECUTOR RECEIVED")
        print("INDEX   :", index)
        print("BALANCE :", balance)
        print("SIGNAL  :", signal)
        print("=" * 60)
        if not isinstance(signal, dict):
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_SIGNAL", reason="Signal must be a dictionary", signal=signal)
        execution, event = self._get_execution(signal), self._get_event(signal)
        if self._is_rejected_signal(signal):
            self.total_rejected += 1
            return self._result(balance=balance, rejected=True, status="FILTER_REJECTED", reason=signal.get("rejection_reasons", ["SIGNAL_REJECTED"]), signal=signal)
        if execution in ("", "NONE", "NO_ACTION", "NO_SIGNAL", "HOLD", "WAIT"):
            self.total_ignored += 1
            return self._result(balance=balance, ignored=True, status="NO_EXECUTION", reason="Signal contains no executable action", signal=signal)
        if self._is_exit_signal(signal) and self._is_event_driven_strategy(signal):
            self.total_exit_signals += 1
            exit_direction = self._map_exit_direction(signal)
            if exit_direction is None:
                self.total_ignored += 1
                return self._result(balance=balance, ignored=True, status="UNKNOWN_EXIT_DIRECTION", reason="Could not determine the position direction for the exit signal", signal=signal)
            close, time = self._get_engine_array(engine, "close", "closes", "close_prices"), self._get_engine_array(engine, "time")
            if close is None or time is None:
                self.total_invalid += 1
                return self._result(balance=balance, ignored=True, status="MISSING_EXIT_MARKET_DATA", reason="Close or time array is unavailable", signal=signal)
            try:
                exit_price, exit_time = float(close[index]), time[index]
            except (IndexError, KeyError, TypeError, ValueError):
                self.total_invalid += 1
                return self._result(balance=balance, ignored=True, status="INVALID_EXIT_INDEX", reason=f"Exit index {index} is unavailable", signal=signal)
            if not self._is_valid_number(exit_price):
                self.total_invalid += 1
                return self._result(balance=balance, ignored=True, status="INVALID_EXIT_PRICE", reason=f"Invalid exit price at index {index}", signal=signal)
            def calculate_position_profit(open_trade):
                return self.backtest_engine.calculate_profit(symbol=self.backtest_engine.current_symbol, lot_size=float(open_trade.get("lot_size", 0.0)), price_open=float(open_trade.get("entry", 0.0)), price_close=float(exit_price), direction=open_trade.get("direction", exit_direction))
            closed_positions = self.trade_manager.close_positions_by_direction(direction=exit_direction, price=float(exit_price), profit_calculator=calculate_position_profit, status=event)
            if not closed_positions:
                self.total_ignored += 1
                return self._result(balance=balance, ignored=True, status="NO_MATCHING_OPEN_POSITION", reason=f"No open {exit_direction} positions were found for this exit", signal=signal)
            running_balance, individual_results = float(balance), []
            for closed_trade in closed_positions:
                actual_profit = self._get_trade_value(closed_trade, "profit", 0.0)
                if not self._is_valid_number(actual_profit):
                    actual_profit = 0.0
                actual_profit = float(actual_profit)
                balance_before = running_balance
                running_balance += actual_profit
                entry_signal = self._get_trade_value(closed_trade, "signal", {})
                if not isinstance(entry_signal, dict): entry_signal = {}
                entry_time = self._get_trade_value(closed_trade, "open_time", None)
                result_name = "WIN" if actual_profit > 0.0 else "LOSS" if actual_profit < 0.0 else "BREAKEVEN"
                closed_trade = self._update_closed_trade_features(closed_trade, result_name, actual_profit, balance_before, event, float(exit_price), index, exit_time)
                self._append_log(closed_trade, entry_time, exit_time, entry_signal)
                is_win, is_loss = actual_profit > 0.0, actual_profit < 0.0
                if is_win:
                    self.total_wins += 1
                elif is_loss: self.total_losses += 1
                individual_results.append(self._result(balance=running_balance, win=is_win, loss=is_loss, executed=True, status=event, reason="EVENT_EXIT", signal=entry_signal, trade=closed_trade, profit=actual_profit))
            self.total_executed += len(individual_results)
            combined_result = self._result(balance=running_balance, executed=True, status=event, reason=f"Closed {len(individual_results)} {exit_direction} positions", signal=signal, profit=running_balance - float(balance))
            combined_result["trade_results"] = individual_results
            return combined_result
        direction = self._map_direction(signal)
        if direction is None:
            self.total_ignored += 1
            return self._result(balance=balance, ignored=True, status="UNKNOWN_EXECUTION", reason=f"Unsupported execution: {execution}", signal=signal)
        close = self._get_engine_array(engine, "close", "closes", "close_prices")
        high = self._get_engine_array(engine, "high", "highs")
        low = self._get_engine_array(engine, "low", "lows")
        time = self._get_engine_array(engine, "time")
        atr = self._get_engine_array(engine, "atr", "atr14", "atr_14")
        required_arrays = {"close": close, "high": high, "low": low, "time": time, "atr": atr}
        missing_arrays = [name for name, values in required_arrays.items() if values is None]
        if missing_arrays:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="MISSING_MARKET_DATA", reason="Missing engine arrays: " + ", ".join(missing_arrays), signal=signal)
        try:
            entry_price, entry_atr, entry_time = close[index], atr[index], time[index]
        except (IndexError, TypeError, KeyError):
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_INDEX", reason=f"Index {index} is unavailable", signal=signal)
        if not self._is_valid_number(entry_price):
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_ENTRY_PRICE", reason=f"Invalid close price at index {index}", signal=signal)
        if not self._is_valid_number(entry_atr) or float(entry_atr) <= 0.0:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_ATR", reason=f"ATR is unavailable or invalid at index {index}", signal=signal)
        if not self._is_valid_number(balance) or float(balance) <= 0.0:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_BALANCE", reason="Balance must be greater than zero", signal=signal)
        trade_data = self.backtest_engine.prepare_trade(direction=direction, entry=float(entry_price), atr=float(entry_atr), balance=float(balance), risk_percent=self.risk_percent, rr=self.rr)
        if not isinstance(trade_data, dict):
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="TRADE_PREPARATION_FAILED", reason="BacktestEngine.prepare_trade returned no valid trade data", signal=signal)
        required_trade_fields = ("risk_amount", "lot_size", "entry", "sl", "tp", "atr", "stop")
        missing_trade_fields = [field for field in required_trade_fields if field not in trade_data]
        if missing_trade_fields:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INCOMPLETE_TRADE_DATA", reason="Missing trade fields: " + ", ".join(missing_trade_fields), signal=signal)
        risk_amount, lot_size, entry, sl, tp = trade_data["risk_amount"], trade_data["lot_size"], trade_data["entry"], trade_data["sl"], trade_data["tp"]
        numeric_trade_values = {"risk_amount": risk_amount, "lot_size": lot_size, "entry": entry, "sl": sl, "tp": tp}
        invalid_trade_values = [name for name, value in numeric_trade_values.items() if not self._is_valid_number(value)]
        if invalid_trade_values:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_TRADE_DATA", reason="Invalid trade values: " + ", ".join(invalid_trade_values), signal=signal)
        if float(lot_size) <= 0.0:
            self.total_invalid += 1
            return self._result(balance=balance, ignored=True, status="INVALID_LOT_SIZE", reason="Calculated lot size must be greater than zero", signal=signal)
        # =====================================================
        # EXECUTOR SCORE AUDIT
        # =====================================================
        if signal.get("execution"):
            print(
                "[EXECUTOR SCORE AUDIT]",
                "EVENT =", signal.get("event"),
                "EXECUTION =", signal.get("execution"),
                "SCORE =", signal.get("score"),
            )

        trade = self.trade_manager.create_trade(direction=direction, entry=float(entry), stop_loss=float(sl), take_profit=float(tp), lot_size=float(lot_size), open_time=entry_time)
        if trade is None:
            self.total_open_failed += 1
            return self._result(balance=balance, ignored=True, status="CREATE_TRADE_FAILED", reason="TradeManager.create_trade returned None", signal=signal)
        trade = self._attach_signal_metadata(trade=trade, signal=signal, direction=direction, index=index)
        features = self._get_trade_value(trade, "features", {})
        if isinstance(features, dict):
            features["entry_time"] = entry_time
            features["entry_price"] = float(entry)
            features["symbol"] = self.backtest_engine.current_symbol
            self._set_trade_value(trade, "features", features)
        print("=" * 60)
        print("POSITION SIZE")
        print("Strategy :", signal.get("strategy", ""))
        print("Event    :", event)
        print("Type     :", self._get_entry_type(signal))
        print("Direction:", direction)
        print("Balance  :", balance)
        print("Risk $   :", risk_amount)
        print("ATR      :", trade_data["atr"])
        print("STOP ATR :", trade_data["stop"])
        print("Lot      :", lot_size)
        print("Score    :", signal.get("score", 0))
        print("Class    :", signal.get("quality_class", ""))
        print("=" * 60)
        trade = self.trade_manager.open_trade(trade)

        # =====================================================
        # TRADE DIAGNOSTICS INITIALIZATION
        # =====================================================

        trade["entry_index"] = index
        trade["last_index"] = index

        if trade is None:
            self.total_open_failed += 1
            return self._result(balance=balance, ignored=True, status="OPEN_TRADE_FAILED", reason="TradeManager rejected or failed to open the trade", signal=signal)
        self.total_executed += 1
        if self._is_event_driven_strategy(signal):
            return self._result(balance=balance, executed=True, status="EVENT_POSITION_OPENED", reason="Position opened and waiting for the strategy exit event", signal=signal, trade=trade)
        sl_index, tp_index = self.backtest_engine.simulate_trade(direction=direction, sl=float(sl), tp=float(tp), high=high, low=low, index=index)
        target_hit = tp_index != -1 and (sl_index == -1 or tp_index < sl_index)
        if target_hit:
            profit = self.backtest_engine.calculate_profit(symbol=self.backtest_engine.current_symbol, lot_size=float(lot_size), price_open=float(entry), price_close=float(tp), direction=direction)
            trade = self.trade_manager.close_trade(price=float(tp), profit=float(profit), status="TARGET")
            if trade is None:
                self.total_invalid += 1
                return self._result(balance=balance, executed=True, status="CLOSE_TRADE_FAILED", reason="Trade reached target but TradeManager.close_trade failed", signal=signal)
            actual_profit = self._get_trade_value(trade, "profit", profit)
            if not self._is_valid_number(actual_profit):
                actual_profit = float(profit)
            exit_time = time[tp_index] if 0 <= tp_index < len(time) else None
            trade = self._update_closed_trade_features(trade, "WIN", actual_profit, float(balance), "TARGET", float(tp), tp_index, exit_time)
            self._append_log(trade, entry_time, exit_time, signal)
            self.total_wins += 1
            return self._result(balance=float(balance) + float(actual_profit), win=True, executed=True, status="TARGET", reason="TAKE_PROFIT_HIT", signal=signal, trade=trade, profit=actual_profit)
        if sl_index != -1:
            calculated_loss = self.backtest_engine.calculate_profit(symbol=self.backtest_engine.current_symbol, lot_size=float(lot_size), price_open=float(entry), price_close=float(sl), direction=direction)
            loss_value = -abs(float(calculated_loss))
            trade = self.trade_manager.close_trade(price=float(sl), profit=loss_value, status="STOPPED")
            if trade is None:
                self.total_invalid += 1
                return self._result(balance=balance, executed=True, status="CLOSE_TRADE_FAILED", reason="Trade reached stop but TradeManager.close_trade failed", signal=signal)
            actual_profit = self._get_trade_value(trade, "profit", loss_value)
            if not self._is_valid_number(actual_profit):
                actual_profit = loss_value
            actual_profit = -abs(float(actual_profit))
            exit_time = time[sl_index] if 0 <= sl_index < len(time) else None
            trade = self._update_closed_trade_features(trade, "LOSS", actual_profit, float(balance), "STOPPED", float(sl), sl_index, exit_time)
            self._append_log(trade, entry_time, exit_time, signal)
            self.total_losses += 1
            return self._result(balance=float(balance) + float(actual_profit), loss=True, executed=True, status="STOPPED", reason="STOP_LOSS_HIT", signal=signal, trade=trade, profit=actual_profit)
        self.total_still_open += 1
        return self._result(balance=balance, executed=True, status="STILL_OPEN", reason="Neither stop loss nor target was hit inside the simulation window", signal=signal, trade=trade)

    # =====================================================
    # EXECUTOR STATISTICS
    # =====================================================
    def get_statistics(self):
        decided_signals = self.total_wins + self.total_losses
        win_rate = self.total_wins / decided_signals * 100.0 if decided_signals > 0 else 0.0
        return {"total_received": self.total_received, "total_executed": self.total_executed, "total_rejected": self.total_rejected, "total_ignored": self.total_ignored, "total_invalid": self.total_invalid, "total_open_failed": self.total_open_failed, "total_wins": self.total_wins, "total_losses": self.total_losses, "total_still_open": self.total_still_open, "total_exit_signals": self.total_exit_signals, "win_rate": win_rate}