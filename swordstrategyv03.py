# ==========================================================
# HAZ TRADE
# STRATEGY : SwordStrategyV03
# VERSION : V1.14
# PHASE 2D
# ENTRY EXECUTION CONFIRMATION
# ==========================================================
from core.indicator_engine import cci_np, ema_np, lux_bbands_bo_np, supertrend_np, crossover_np, crossunder_np

class SwordStrategyV03:
    # ======================================================
    # INITIALIZATION
    # ======================================================
    def __init__(self):
        self.initialized = False
        self.in_short_environment = False
        self.in_long_environment = False
        self.short_mother_open = False
        self.long_mother_open = False
        # ======================================================
        # EXECUTION CONFIRMATION STATE
        # TradeManager remains the source of truth.
        # ======================================================
        self.short_entry_pending = False
        self.long_entry_pending = False
        self.short_exit_pending = False
        self.long_exit_pending = False
        # ======================================================
        # SWORD TRIGGER MEMORY
        # ======================================================
        self.short_trigger_ready = False
        self.long_trigger_ready = False
        # ======================================================
        # TRIGGER AGE MEMORY
        # ======================================================
        self.short_trigger_age = 0
        self.long_trigger_age = 0
        self.max_trigger_age = 100
        ##self.lux_min_strength = 0.896
        ##self.lux_max_strength = 10.943
        self.lux_min_strength = 0.896
        self.lux_max_strength = 2.317
        # ======================================================
        # ADD-ON STATE
        # ======================================================
        self.short_addon_count = 0
        self.long_addon_count = 0
        self.prev_ema_sell = False
        self.prev_ema_buy = False
        # ======================================================
        # DEBUG COUNTERS
        # ======================================================
        self.debug = {
            "short_env": 0, "long_env": 0, "cci_short_trigger": 0, "cci_long_trigger": 0,
            "ema_sell": 0, "ema_buy": 0, "lux_sell": 0, "lux_buy": 0,
            "short_mother_ready": 0, "long_mother_ready": 0,
            "short_mother_open": 0, "long_mother_open": 0,
            "short_trigger_stored": 0, "long_trigger_stored": 0,
            "short_trigger_expired": 0, "long_trigger_expired": 0,
            "short_addon_ready": 0, "long_addon_ready": 0,
            "short_exit": 0, "long_exit": 0,
            "short_blocked_already_open": 0, "long_blocked_already_open": 0,
            "h4_blocked_long": 0, "h4_blocked_short": 0,
        }

    # ======================================================
    # TRADE MANAGER STATE SYNCHRONIZATION
    # ======================================================
    def synchronize_position_state(self, has_long_position, has_short_position):
        self.long_mother_open = bool(has_long_position)
        self.short_mother_open = bool(has_short_position)

        if self.long_mother_open:
            self.long_entry_pending = False
        else:
            self.long_exit_pending = False
            self.long_addon_count = 0

        if self.short_mother_open:
            self.short_entry_pending = False
        else:
            self.short_exit_pending = False
            self.short_addon_count = 0

    # ======================================================
    # EXECUTION CONFIRMATION CALLBACK
    # ======================================================
    def confirm_execution(self, execution, success):
        execution = str(execution or "").strip().upper()

        if not success:
            if execution == "OPEN_LONG":
                self.long_entry_pending = False
            elif execution == "OPEN_SHORT":
                self.short_entry_pending = False
            elif execution == "EXIT_LONG":
                self.long_exit_pending = False
            elif execution == "EXIT_SHORT":
                self.short_exit_pending = False
            return

        if execution == "OPEN_LONG":
            self.long_entry_pending = False
            self.long_mother_open = True
            self.short_mother_open = False
            self.short_trigger_ready = False
            self.long_trigger_ready = False
            self.short_trigger_age = 0
            self.long_trigger_age = 0
            self.debug["long_mother_open"] += 1

        elif execution == "OPEN_SHORT":
            self.short_entry_pending = False
            self.short_mother_open = True
            self.long_mother_open = False
            self.short_trigger_ready = False
            self.long_trigger_ready = False
            self.short_trigger_age = 0
            self.long_trigger_age = 0
            self.debug["short_mother_open"] += 1

        elif execution == "EXIT_LONG":
            self.long_mother_open = False
            self.long_exit_pending = False
            self.long_addon_count = 0
            self.long_trigger_ready = False
            self.long_trigger_age = 0

        elif execution == "EXIT_SHORT":
            self.short_mother_open = False
            self.short_exit_pending = False
            self.short_addon_count = 0
            self.short_trigger_ready = False
            self.short_trigger_age = 0

    # ======================================================
    # INITIALIZE INDICATORS
    # ======================================================
    def initialize(self, engine):
        if self.initialized: return
        print("[SWORDSTRATEGYV03] Initializing Indicators...")
        # ======================================================
        # CCI CORE
        # ======================================================
        self.cci, self.cci_ma = cci_np(high=engine["high"], low=engine["low"], close=engine["close"], volume=engine["volume"], period=180, ma_period=200, upper_band=90, lower_band=-90)
        # ======================================================
        # EMA STRUCTURE
        # ======================================================
        self.ema50 = ema_np(engine["close"], 50)
        self.ema100 = ema_np(engine["close"], 100)
        self.ema200 = ema_np(engine["close"], 200)
        # ======================================================
        # EMA18 / EMA81 WAVE
        # ======================================================
        self.ema18 = ema_np(engine["close"], 18)
        self.ema81 = ema_np(engine["close"], 81)
        # ======================================================
        # EMA50 / EMA100 EVENTS
        # ======================================================
        self.entry_sell = crossunder_np(self.ema50, self.ema100)
        self.entry_buy = crossover_np(self.ema50, self.ema100)
        # ======================================================
        # SWORD V03 SUPERTREND ATR EXIT ENGINE
        # ATR LENGTH = 18 | ATR MULTIPLIER = 2
        # ======================================================
        self.supertrend, self.supertrend_direction, self.supertrend_atr = supertrend_np(
            high=engine["high"],
            low=engine["low"],
            close=engine["close"],
            atr_length=18,
            atr_multiplier=2,
        )
        self.exit_sell = crossover_np(engine["close"], self.supertrend)
        self.exit_buy = crossunder_np(engine["close"], self.supertrend)
        # ======================================================
        # LUX BBANDS BREAKOUT OSCILLATOR
        # ======================================================
        self.lux_bull, self.lux_bear = lux_bbands_bo_np(high=engine["high"], low=engine["low"], close=engine["close"], length=81, mult=1.8)
        self.initialized = True
        print("[HAZ] Loaded Strategy : SwordStrategyV03")
        print("[SWORDSTRATEGYV03] Ready")

    # ======================================================
    # GENERATE SIGNAL
    # ======================================================
    def generate(self, symbol, engine, index):
        print("===== SWORDSTRATEGYV03 GENERATE ACTIVE =====", index)
        if not self.initialized: self.initialize(engine)
        i = index
        # =====================================================
        # HTF ROUTER VALUES
        # =====================================================
        htf_router_ready = bool(engine["htf_router_ready"][i])
        htf_long_allowed = bool(engine["htf_long_allowed"][i])
        htf_short_allowed = bool(engine["htf_short_allowed"][i])
        # =====================================================
        # BAR STATE
        # =====================================================
        mother_opened_this_bar = False
        # =====================================================
        # READ VALUES
        # =====================================================
        cci, cci_ma = self.cci[i], self.cci_ma[i]
        ema50, ema100, ema200 = self.ema50[i], self.ema100[i], self.ema200[i]
        ema18, ema81 = self.ema18[i], self.ema81[i]
        lux_bull, lux_bear = self.lux_bull[i], self.lux_bear[i]
        lux_strength = abs(lux_bull - lux_bear)
        lux_strength_ok = self.lux_min_strength < lux_strength <= self.lux_max_strength
        supertrend = self.supertrend[i]
        supertrend_direction = self.supertrend_direction[i]
        supertrend_atr = self.supertrend_atr[i]
        exit_sell, exit_buy = self.exit_sell[i], self.exit_buy[i]
        entry_sell, entry_buy = self.entry_sell[i], self.entry_buy[i]
        # =====================================================
        # ENVIRONMENT
        # =====================================================
        self.in_short_environment = cci_ma < 0
        self.in_long_environment = cci_ma > 0
        # =====================================================
        # RESET TRIGGER WHEN ENVIRONMENT CHANGES
        # =====================================================
        if not self.in_short_environment:
            self.short_trigger_ready = False
            self.short_trigger_age = 0
        if not self.in_long_environment and self.long_trigger_ready:
            print("LONG TRIGGER LOST", "INDEX =", i, "AGE =", self.long_trigger_age)
            self.long_trigger_ready = False
            self.long_trigger_age = 0
        if self.in_short_environment: self.debug["short_env"] += 1
        if self.in_long_environment: self.debug["long_env"] += 1
        # =====================================================
        # EMA STRUCTURE
        # =====================================================
        ema_sell = ema50 < ema100 < ema200
        ema_buy = ema50 > ema100 > ema200
        if ema_sell: self.debug["ema_sell"] += 1
        if ema_buy: self.debug["ema_buy"] += 1
        # =====================================================
        # LUX DOMINANCE
        # =====================================================
        lux_sell = lux_bear > lux_bull and lux_bear > 0
        lux_buy = lux_bull > lux_bear and lux_bull > 0
        self.prev_lux_sell = False
        self.prev_lux_buy = False
        lux_sell_event = lux_sell and not self.prev_lux_sell
        lux_buy_event = lux_buy and not self.prev_lux_buy
        if lux_sell: self.debug["lux_sell"] += 1
        if lux_buy: self.debug["lux_buy"] += 1
        # =====================================================
        # CCI EVENTS
        # =====================================================
        cci_cross_down = self.cci[i - 1] > -90 and self.cci[i] <= -90
        cci_cross_up = self.cci[i - 1] < 90 and self.cci[i] >= 90
        # =====================================================
        # STORE CCI EVENT INSIDE ENVIRONMENT
        # =====================================================
        if self.in_short_environment and cci_cross_down:
            self.short_trigger_ready = True
            self.short_trigger_age = 0
            self.debug["short_trigger_stored"] += 1
            self.debug["cci_short_trigger"] += 1
            print("=" * 80)
            print("SHORT TRIGGER STORED")
            print("INDEX :", i)
            print("AGE :", self.short_trigger_age)
            print("EMA :", ema_sell)
            print("LUX :", lux_sell)
            print("SHORT ENV :", self.in_short_environment)
            print("=" * 80)
        if self.in_long_environment and cci_cross_up:
            self.long_trigger_ready = True
            self.long_trigger_age = 0
            self.debug["long_trigger_stored"] += 1
            self.debug["cci_long_trigger"] += 1
            print("LONG TRIGGER CREATED", "INDEX =", i)
            print("=" * 80)
            print("LONG TRIGGER STORED")
            print("INDEX :", i)
            print("AGE :", self.long_trigger_age)
            print("EMA :", ema_buy)
            print("LUX :", lux_buy)
            print("LONG ENV :", self.in_long_environment)
            print("=" * 80)
        # =====================================================
        # TRIGGER AGE CONTROL
        # =====================================================
        if self.short_trigger_ready:
            self.short_trigger_age += 1
            if self.short_trigger_age >= self.max_trigger_age:
                self.short_trigger_ready = False
                self.debug["short_trigger_expired"] += 1
        if self.long_trigger_ready:
            self.long_trigger_age += 1
            if self.long_trigger_age >= self.max_trigger_age:
                self.long_trigger_ready = False
                self.debug["long_trigger_expired"] += 1
        print("TRIGGER STATUS:", self.short_trigger_ready, self.long_trigger_ready)
        print("CHECK:", "SHORT_ENV=", self.in_short_environment, "LONG_ENV=", self.in_long_environment, "CCI_DOWN=", cci_cross_down, "CCI_UP=", cci_cross_up, "EMA_SELL=", ema_sell, "EMA_BUY=", ema_buy, "LUX_SELL=", lux_sell, "LUX_BUY=", lux_buy)
        # =====================================================
        # EVENTS
        # =====================================================
        event = None
        direction = None
        execution = None
        # =====================================================
        # SUPERTREND ATR EXIT EVENTS
        # SHORT closes when candle close crosses above SuperTrend.
        # LONG closes when candle close crosses below SuperTrend.
        # EMA18 / EMA81 remains available for Add-On logic only.
        # =====================================================
        if self.short_mother_open:
            print("SHORT OPEN", i, "SUPERTREND EXIT=", exit_sell, "CLOSE=", round(engine["close"][i], 5), "SUPERTREND=", round(supertrend, 5))
        if self.long_mother_open:
            print("LONG OPEN", i, "SUPERTREND EXIT=", exit_buy, "CLOSE=", round(engine["close"][i], 5), "SUPERTREND=", round(supertrend, 5))
        if self.short_mother_open and not self.short_exit_pending and exit_sell:
            event, direction = "SHORT_EXIT", "EXIT"
            self.short_exit_pending = True
            self.debug["short_exit"] += 1
        elif self.long_mother_open and not self.long_exit_pending and exit_buy:
            event, direction = "LONG_EXIT", "EXIT"
            self.long_exit_pending = True
            self.debug["long_exit"] += 1
        # =====================================================
        # MOTHER CONDITIONS
        # =====================================================
        short_mother = event is None and not self.short_entry_pending and not self.short_exit_pending and self.in_short_environment and self.short_trigger_ready and htf_router_ready and htf_short_allowed and (ema_sell or lux_sell) and lux_strength_ok
        long_mother = event is None and not self.long_entry_pending and not self.long_exit_pending and self.in_long_environment and self.long_trigger_ready and htf_router_ready and htf_long_allowed and (ema_buy or lux_buy) and lux_strength_ok
        if short_mother:
            self.debug["short_mother_ready"] += 1
            print("=" * 70)
            print("SHORT MOTHER READY")
            print("INDEX :", i)
            print("TIME  :", engine["time"][i])
            print("OPEN STATE :", self.short_mother_open)
            print("=" * 70)
        if long_mother:
            self.debug["long_mother_ready"] += 1
            print("=" * 70)
            print("LONG MOTHER READY")
            print("INDEX :", i)
            print("TIME  :", engine["time"][i])
            print("OPEN STATE :", self.long_mother_open)
            print("=" * 70)
        print("MOTHER RESULT:", short_mother, long_mother)
        # =====================================================
        # TRIGGER MEMORY DEBUG
        # =====================================================
        if self.short_trigger_ready:
            print("=" * 70)
            print("SHORT MEMORY ACTIVE")
            print("INDEX :", i)
            print("AGE   :", self.short_trigger_age)
            print("EMA   :", ema_sell)
            print("LUX   :", lux_sell)
            print("MOTHER:", short_mother)
            print("=" * 70)
        if self.long_trigger_ready:
            print("=" * 70)
            print("LONG MEMORY ACTIVE")
            print("INDEX :", i)
            print("AGE   :", self.long_trigger_age)
            print("EMA   :", ema_buy)
            print("LUX   :", lux_buy)
            print("MOTHER:", long_mother)
            print("=" * 70)
        # =====================================================
        # ADD-ON CONDITIONS
        # =====================================================
        short_addon = event is None and not self.short_exit_pending and self.short_mother_open and self.short_addon_count < 2 and self.in_short_environment and htf_router_ready and htf_short_allowed and ema18 < ema81 and lux_sell and lux_strength_ok
        long_addon = event is None and not self.long_exit_pending and self.long_mother_open and self.long_addon_count < 2 and self.in_long_environment and htf_router_ready and htf_long_allowed and ema18 > ema81 and lux_buy and lux_strength_ok
        # =====================================================
        # ADD-ON QUALITY
        # =====================================================
        short_addon_quality = abs(cci) >= 120 and lux_bear >= 10
        long_addon_quality = abs(cci) >= 120 and lux_bull >= 10
        print("MOTHER CHECK:", "SHORT_ENV=", self.in_short_environment, "TRIGGER=", self.short_trigger_ready, "EMA=", ema_sell, "LUX=", lux_sell, "LONG_ENV=", self.in_long_environment, "LONG_TRIGGER=", self.long_trigger_ready, "LONG_EMA=", ema_buy, "LONG_LUX=", lux_buy)
        # =====================================================
        # MOTHER ENTRY
        # =====================================================
        if short_mother and self.short_mother_open:
            self.debug["short_blocked_already_open"] += 1
            print("BLOCKED SHORT MOTHER")
            print("INDEX :", i)
        if long_mother and self.long_mother_open:
            self.debug["long_blocked_already_open"] += 1
            print("BLOCKED LONG MOTHER")
            print("INDEX :", i)
        if short_mother or long_mother:
            print("=" * 60)
            print("MOTHER READY DETECTED")
            print("INDEX :", i)
            print("SHORT READY :", short_mother)
            print("SHORT OPEN  :", self.short_mother_open)
            print("LONG READY  :", long_mother)
            print("LONG OPEN   :", self.long_mother_open)
            print("EVENT :", event)
            print("=" * 60)
        if short_mother and not self.short_mother_open:
            self.short_entry_pending = True
            self.short_addon_count = 0
            self.long_addon_count = 0
            mother_opened_this_bar = True
            event, direction, execution = "SHORT_MOTHER", "SELL", "OPEN_SHORT"
            self.short_open_index = i
            print("=" * 60)
            print(">>> SHORT MOTHER EXECUTION REQUEST <<<")
            print("INDEX   :", i)
            print("TIME    :", engine["time"][i])
            print("PENDING :", self.short_entry_pending)
            print("=" * 60)
        elif long_mother and not self.long_mother_open:
            self.long_entry_pending = True
            self.short_addon_count = 0
            self.long_addon_count = 0
            mother_opened_this_bar = True
            event, direction, execution = "LONG_MOTHER", "BUY", "OPEN_LONG"
            self.long_open_index = i
            print("=" * 60)
            print(">>> LONG MOTHER EXECUTION REQUEST <<<")
            print("INDEX   :", i)
            print("TIME    :", engine["time"][i])
            print("PENDING :", self.long_entry_pending)
            print("=" * 60)
        # =====================================================
        # ADD-ON EVENTS
        # =====================================================
        elif short_addon and short_addon_quality and not mother_opened_this_bar:
            self.short_addon_count += 1
            self.debug["short_addon_ready"] += 1
            event, direction, execution = "SHORT_ADDON", "SELL", "ADD_SHORT"
        elif long_addon and long_addon_quality and not mother_opened_this_bar:
            self.long_addon_count += 1
            self.debug["long_addon_ready"] += 1
            event, direction, execution = "LONG_ADDON", "BUY", "ADD_LONG"
        # =====================================================
        # DEBUG
        # =====================================================
        print("=" * 60)
        print("SWORDSTRATEGYV03 :", symbol)
        print("INDEX :", i)
        print("------------------------------------")
        print("CCI       :", round(cci, 2))
        print("CCI MA    :", round(cci_ma, 2))
        print("------------------------------------")
        print(f"EMA50  : {ema50:.5f}")
        print(f"EMA100 : {ema100:.5f}")
        print(f"EMA200 : {ema200:.5f}")
        print(f"EMA18  : {ema18:.5f}")
        print(f"EMA81  : {ema81:.5f}")
        print("------------------------------------")
        print("SUPERTREND :", round(supertrend, 5))
        print("ST DIRECTION :", int(supertrend_direction))
        print("ST ATR18 :", round(supertrend_atr, 5))
        print("------------------------------------")
        print("LUX BULL :", round(lux_bull, 2))
        print("LUX BEAR :", round(lux_bear, 2))
        print("------------------------------------")
        print("SHORT ENV :", self.in_short_environment)
        print("LONG ENV  :", self.in_long_environment)
        print("------------------------------------")
        print("HTF ROUTER READY  :", htf_router_ready)
        print("HTF SHORT ALLOWED :", htf_short_allowed)
        print("HTF LONG ALLOWED  :", htf_long_allowed)
        print("------------------------------------")
        print("TRIGGER SHORT :", self.short_trigger_ready)
        print("TRIGGER LONG  :", self.long_trigger_ready)
        print("------------------------------------")
        print("EVENT :", event)
        print("DIRECTION :", direction)
        print("=" * 60)
        # =====================================================
        # SIGNAL SCORE
        # =====================================================
        score = 0
        if event in ("SHORT_MOTHER", "LONG_MOTHER"): score += 70
        if lux_buy or lux_sell: score += 10
        if ema_buy or ema_sell: score += 10
        if self.short_trigger_ready or self.long_trigger_ready: score += 10
        # =====================================================
        # EXECUTION MAPPING
        # =====================================================
        if event == "LONG_MOTHER": execution = "OPEN_LONG"
        elif event == "SHORT_MOTHER": execution = "OPEN_SHORT"
        elif event == "LONG_ADDON": execution = "ADD_LONG"
        elif event == "SHORT_ADDON": execution = "ADD_SHORT"
        elif event == "LONG_EXIT": execution = "EXIT_LONG"
        elif event == "SHORT_EXIT": execution = "EXIT_SHORT"
        # =====================================================
        # FINAL H4 ROUTER SAFETY GUARD
        # =====================================================
        if execution in ("OPEN_LONG", "ADD_LONG") and not (htf_router_ready and htf_long_allowed):
            self.debug["h4_blocked_long"] += 1
            print("[H4 BLOCKED LONG]", "INDEX =", i, "READY =", htf_router_ready, "LONG_ALLOWED =", htf_long_allowed)
            event, direction, execution, score = None, None, None, 0
        elif execution in ("OPEN_SHORT", "ADD_SHORT") and not (htf_router_ready and htf_short_allowed):
            self.debug["h4_blocked_short"] += 1
            print("[H4 BLOCKED SHORT]", "INDEX =", i, "READY =", htf_router_ready, "SHORT_ALLOWED =", htf_short_allowed)
            event, direction, execution, score = None, None, None, 0
        print("FINAL EVENT:", event, execution)
        # =====================================================
        # NORMALIZE EVENT CLASSIFICATION
        # =====================================================
        mother = event in ("SHORT_MOTHER", "LONG_MOTHER")
        addon = event in ("SHORT_ADDON", "LONG_ADDON")
        trend_ok = htf_long_allowed if direction == "BUY" else htf_short_allowed if direction == "SELL" else None
        # =====================================================
        # SIGNAL PACKAGE
        # =====================================================
        signal = {
            "strategy": "swordstrategyv03",
            "execution": execution,
            "score": score,
            "event": event,
            "direction": direction,
            "mother": mother,
            "addon": addon,
            "short_environment": self.in_short_environment,
            "long_environment": self.in_long_environment,
            "short_mother": short_mother,
            "long_mother": long_mother,
            "short_entry_pending": self.short_entry_pending,
            "long_entry_pending": self.long_entry_pending,
            "short_exit_pending": self.short_exit_pending,
            "long_exit_pending": self.long_exit_pending,
            "short_addon": short_addon,
            "long_addon": long_addon,
            "cci": cci,
            "cci_ma": cci_ma,
            "ema50": ema50,
            "ema100": ema100,
            "ema200": ema200,
            "ema18": ema18,
            "ema81": ema81,
            "supertrend": supertrend,
            "supertrend_direction": int(supertrend_direction),
            "supertrend_atr": supertrend_atr,
            "supertrend_atr_length": 18,
            "supertrend_atr_multiplier": 2,
            "exit_reason": "SUPERTREND_ATR_18_2" if event in ("LONG_EXIT", "SHORT_EXIT") else None,
            "ema_sell": ema_sell,
            "ema_buy": ema_buy,
            "lux_bull": lux_bull,
            "lux_bear": lux_bear,
            "lux_strength": lux_strength,
            "lux_range": lux_strength,
            "htf_router_ready": htf_router_ready,
            "htf_long_allowed": htf_long_allowed,
            "htf_short_allowed": htf_short_allowed,
            "trend_ok": trend_ok,
            "ema_ok": ema_buy if direction == "BUY" else ema_sell if direction == "SELL" else None,
        }

        # =====================================================
        # SWORD SCORE AUDIT
        # =====================================================
        if execution:
            print(
                "[SWORD SCORE AUDIT]",
                "INDEX =", i,
                "EVENT =", event,
                "EXECUTION =", execution,
                "STRATEGY SCORE =", score,
            )

        # =====================================================
        # DEBUG COUNTERS REPORT
        # =====================================================
        if i == len(engine["close"]) - 301:
            print("=" * 60)
            print("SWORDSTRATEGYV03 DEBUG COUNTERS")
            print(self.debug)
            print("=" * 60)
        # =====================================================
        # FINAL ROUTER ASSERTIONS
        # =====================================================
        if execution in ("OPEN_LONG", "ADD_LONG"):
            assert signal["htf_router_ready"] and signal["htf_long_allowed"], f"INVALID LONG ENTRY AT INDEX {i}"
        if execution in ("OPEN_SHORT", "ADD_SHORT"):
            assert signal["htf_router_ready"] and signal["htf_short_allowed"], f"INVALID SHORT ENTRY AT INDEX {i}"

        self.prev_lux_sell = lux_sell
        self.prev_lux_buy = lux_buy

        return signal