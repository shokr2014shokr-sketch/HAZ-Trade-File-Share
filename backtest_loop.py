# ==========================================================
# HAZ TRADE
# BACKTEST LOOP ENGINE
# VERSION : V8.06
# ==========================================================

import numpy as np

from strategies.signal_score import SignalScore
from strategies.feature_engine import FeatureEngine


class BacktestLoop:

    def __init__(

        self,

        signal_engine,

        signal_filter,

        executor,

        metrics,

    ):

        self.signal_engine = signal_engine

        self.signal_filter = signal_filter

        self.executor = executor

        self.metrics = metrics

        self.signal_score = SignalScore()

    # ======================================================
    # RUN LOOP
    # ======================================================

    def run(

        self,

        symbol,

        engine,

        strategy,

    ):

        # ==================================================
        # SELECT STRATEGY
        # ==================================================

        self.signal_engine.set_strategy(strategy)

        close = engine["close"]

        high = engine["high"]

        low = engine["low"]

        sell_liq = engine["sell_liq"]

        buy_liq = engine["buy_liq"]

        vol_ma = engine["vol_ma"]

        trend_index = engine["TREND_TIMEFRAME_index"]

        total = len(close)

        # ==================================================
        # MAIN LOOP
        # ==================================================

        for i in range(200, total - 300):


            # ======================================================
            # UPDATE OPEN TRADE DIAGNOSTICS
            # ======================================================

            for open_trade in self.executor.trade_manager.open_positions:

                entry_price = float(
                    open_trade.get(
                        "entry",
                        0.0,
                    )
                )

                entry_index = int(
                    open_trade.get(
                        "entry_index",
                        i,
                    )
                )

                current_high = float(
                    high[i]
                )

                current_low = float(
                    low[i]
                )

                open_trade["last_index"] = i

                open_trade["bars_in_trade"] = max(
                    0,
                    i - entry_index,
                )

                open_trade["highest_price"] = max(
                    float(
                        open_trade.get(
                            "highest_price",
                            entry_price,
                        )
                    ),
                    current_high,
                )

                open_trade["lowest_price"] = min(
                    float(
                        open_trade.get(
                            "lowest_price",
                            entry_price,
                        )
                    ),
                    current_low,
                )

                direction = str(
                    open_trade.get(
                        "direction",
                        "",
                    )
                ).strip().upper()

                if direction == "LONG":

                    open_trade["mfe"] = max(
                        0.0,
                        open_trade["highest_price"] - entry_price,
                    )

                    open_trade["mae"] = max(
                        0.0,
                        entry_price - open_trade["lowest_price"],
                    )

                elif direction == "SHORT":

                    open_trade["mfe"] = max(
                        0.0,
                        entry_price - open_trade["lowest_price"],
                    )

                    open_trade["mae"] = max(
                        0.0,
                        open_trade["highest_price"] - entry_price,
                    )


            # ==================================================
            # DATA VALIDATION
            # ==================================================

            if (

                np.isnan(sell_liq[i])

                or

                np.isnan(buy_liq[i])

                or

                np.isnan(vol_ma[i])

                or

                trend_index[i] < 1

            ):

                continue

            # ==================================================
            # GENERATE SIGNAL
            # ==================================================

            signal = self.signal_engine.generate(

                symbol=symbol,

                engine=engine,

                index=i,

            )

            if signal is None:

                continue



            print("LOOP EVENT :", signal.get("event"))
            print("LOOP EXEC  :", signal.get("execution"))


            
            if signal and signal.get("event") not in (

                None,

                "NONE",

                "",

            ):


                print()

                print("=" * 70)

                print("[LOOP RECEIVED SIGNAL]")

                print("RAW SIGNAL :", signal)

                print("EVENT      :", signal.get("event"))

                print("DIRECTION  :", signal.get("direction"))

                print("EXECUTION  :", signal.get("execution"))

                print("SCORE      :", signal.get("score"))

                print("=" * 70)



            # ==================================================
            # IGNORE BARS WITHOUT EVENT
            # ==================================================

            if signal.get("event") in (

                None,

                "NONE",

                "",

            ):

                continue



            # ==================================================
            # USE SIGNAL ENGINE QUALITY RESULT
            # ==================================================

            is_exit_signal = bool(

                signal.get(

                    "is_exit_signal",

                    signal.get("event") in (

                        "LONG_EXIT",

                        "SHORT_EXIT",

                    ),

                )

            )


            if not is_exit_signal:

                accepted = bool(

                    signal.get(

                        "accepted",

                        signal.get(

                            "filter_passed",

                            False,

                        ),

                    )

                )


                if not accepted:

                    print(
                        "[SIGNAL REJECTED BY UNIVERSAL QUALITY]",
                        "EVENT:",
                        signal.get("event"),
                        "SCORE:",
                        signal.get("score"),
                        "REASONS:",
                        signal.get(
                            "rejection_reasons",
                            [],
                        ),
                    )

                    continue


            print(
                "[SIGNAL QUALITY ACCEPTED]",
                "EVENT:",
                signal.get("event"),
                "SCORE:",
                signal.get("score"),
                "EXECUTION:",
                signal.get("execution"),
            )

            # ==================================================
            # EXECUTION CHECK
            # ==================================================


            if signal.get("execution") in (

                None,

                "NONE",

                "",


            ):

                continue


            print()

            print("=" * 70)

            print("[SIGNAL SENT TO EXECUTOR]")

            print("INDEX     :", i)

            print("EVENT     :", signal.get("event"))

            print("EXECUTION :", signal.get("execution"))

            print("DIRECTION :", signal.get("direction"))

            print("SCORE     :", signal.get("score"))

            print("=" * 70)


            # ==================================================
            # EXECUTE
            # ==================================================

            result = self.executor.execute(

                signal=signal,

                index=i,

                engine=engine,

                balance=self.metrics.balance,

            )


            if result is None:

                continue

            result["signal"] = signal

            self.metrics.update(result)

        return self.metrics.get_report()