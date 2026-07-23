# ==========================================================
# HAZ TRADE
# UNIVERSAL SIGNAL SCORE
# QUALITY ENGINE
# VERSION : V10.00
# ==========================================================


class SignalScore:

    # ======================================================
    # SCORE CONFIGURATION
    #
    # The universal score is based mainly on shared market
    # quality factors.
    #
    # Strategy-specific features are optional bonuses only.
    # ======================================================

    weights = {

        # ==================================================
        # UNIVERSAL MARKET QUALITY
        # Maximum universal score = 80
        # ==================================================

        "ema_structure": 15,

        "ema_slope": 15,

        "price_position": 10,

        "rsi_direction": 10,

        "macd_direction": 10,

        "adx_strength": 10,

        "atr_safety": 10,


        # ==================================================
        # STRATEGY-SPECIFIC CONFIRMATION
        # Maximum strategy bonus = 20
        # ==================================================

        "strategy_primary_event": 10,

        "strategy_secondary_event": 5,

        "strategy_special_confirmation": 5,

    }


    # ======================================================
    # SAFE BOOLEAN READER
    # ======================================================

    @staticmethod
    def _is_true(

        source,

        key,

    ):

        return bool(

            source.get(

                key,

                False,

            )

        )


    # ======================================================
    # SAFE NUMBER READER
    # ======================================================

    @staticmethod
    def _get_number(

        source,

        key,

        default=0.0,

    ):

        value = source.get(

            key,

            default,

        )

        try:

            return float(value)

        except (

            TypeError,

            ValueError,

        ):

            return float(default)


    # ======================================================
    # DIRECTION NORMALIZATION
    # ======================================================

    @staticmethod
    def _get_direction(

        signal,

    ):

        direction = str(

            signal.get(

                "direction",

                "",

            )

        ).upper()


        execution = str(

            signal.get(

                "execution",

                "",

            )

        ).upper()


        event = str(

            signal.get(

                "event",

                "",

            )

        ).upper()


        if direction in (

            "BUY",

            "LONG",

        ):

            return "LONG"


        if direction in (

            "SELL",

            "SHORT",

        ):

            return "SHORT"


        if "LONG" in execution:

            return "LONG"


        if "SHORT" in execution:

            return "SHORT"


        if "LONG" in event:

            return "LONG"


        if "SHORT" in event:

            return "SHORT"


        return "UNKNOWN"


    # ======================================================
    # STRATEGY EVENT CLASSIFICATION
    #
    # This does not force any strategy to use Mother/Add-On.
    # It recognizes common primary and secondary events.
    # ======================================================

    @staticmethod
    def _classify_strategy_event(

        signal,

        features,

    ):

        event = str(

            signal.get(

                "event",

                "",

            )

        ).upper()


        primary_event = False

        secondary_event = False


        # ==================================================
        # SWORD EVENTS
        # ==================================================

        if features.get(

            "mother",

            False,

        ):

            primary_event = True


        if features.get(

            "addon",

            False,

        ):

            secondary_event = True


        if "MOTHER" in event:

            primary_event = True


        if "ADDON" in event:

            secondary_event = True


        # ==================================================
        # GENERIC STRATEGY EVENTS
        # ==================================================

        if any(

            name in event

            for name in (

                "PRIMARY",

                "ENTRY",

                "BREAKOUT",

                "REVERSAL",

                "MOMENTUM",

                "SWEEP",

                "CONFIRM",

            )

        ):

            primary_event = True


        if any(

            name in event

            for name in (

                "SECONDARY",

                "ADD",

                "PYRAMID",

                "REENTRY",

                "RE_ENTRY",

            )

        ):

            secondary_event = True


        return (

            primary_event,

            secondary_event,

        )


    # ======================================================
    # STRATEGY SPECIAL CONFIRMATION
    #
    # Optional strategy features can contribute a small
    # bonus without dominating the universal score.
    # ======================================================

    @staticmethod
    def _has_special_confirmation(

        features,

    ):

        boolean_keys = (

            "lux_ok",

            "lux_strength_ok",

            "sweep_ok",

            "confirm_ok",

            "mars",

            "news_ok",

            "volume_ok",

            "momentum_ok",

            "breakout_ok",

            "regime_ok",

            "session_ok",

            "validation_ok",

        )


        for key in boolean_keys:

            if features.get(

                key,

                False,

            ):

                return True


        numeric_keys = (

            "lux_strength",

            "signal_strength",

            "confidence",

            "probability",

        )


        for key in numeric_keys:

            value = features.get(

                key,

                None,

            )

            try:

                if (

                    value is not None

                    and

                    float(value) > 0.0

                ):

                    return True

            except (

                TypeError,

                ValueError,

            ):

                continue


        return False


    # ======================================================
    # QUALITY CLASSIFICATION
    # ======================================================

    @staticmethod
    def _quality_class(

        score,

    ):

        if score >= 85:

            return "INSTITUTIONAL"


        if score >= 70:

            return "STRONG"


        if score >= 55:

            return "ACCEPTABLE"


        if score >= 40:

            return "WEAK"


        return "REJECT"


    # ======================================================
    # MAIN SCORE CALCULATION
    # ======================================================

    def calculate(

        self,

        signal,

        filter_result=None,

    ):

        if signal is None:

            signal = {}


        if filter_result is None:

            filter_result = {}


        features = signal.get(

            "features",

            {},

        )


        if not isinstance(

            features,

            dict,

        ):

            features = {}


        if not isinstance(

            filter_result,

            dict,

        ):

            filter_result = {}


        direction = self._get_direction(

            signal

        )


        score = 0


        passed_factors = []

        failed_factors = []


        # ==================================================
        # SELECT DIRECTIONAL FILTER VALUES
        # ==================================================

        if direction == "LONG":

            ema_structure_ok = self._is_true(

                filter_result,

                "long_ema_structure",

            )

            ema_slope_ok = self._is_true(

                filter_result,

                "long_ema_slope",

            )

            price_position_ok = self._is_true(

                filter_result,

                "long_price_position",

            )

            rsi_direction_ok = self._is_true(

                filter_result,

                "long_rsi_ok",

            )

            macd_direction_ok = self._is_true(

                filter_result,

                "long_macd_ok",

            )

            direction_quality_ok = self._is_true(

                filter_result,

                "long_quality_ok",

            )

            filter_quality_score = self._get_number(

                filter_result,

                "long_quality_score",

                0.0,

            )


        elif direction == "SHORT":

            ema_structure_ok = self._is_true(

                filter_result,

                "short_ema_structure",

            )

            ema_slope_ok = self._is_true(

                filter_result,

                "short_ema_slope",

            )

            price_position_ok = self._is_true(

                filter_result,

                "short_price_position",

            )

            rsi_direction_ok = self._is_true(

                filter_result,

                "short_rsi_ok",

            )

            macd_direction_ok = self._is_true(

                filter_result,

                "short_macd_ok",

            )

            direction_quality_ok = self._is_true(

                filter_result,

                "short_quality_ok",

            )

            filter_quality_score = self._get_number(

                filter_result,

                "short_quality_score",

                0.0,

            )


        else:

            ema_structure_ok = False

            ema_slope_ok = False

            price_position_ok = False

            rsi_direction_ok = False

            macd_direction_ok = False

            direction_quality_ok = False

            filter_quality_score = 0.0


        adx_ok = self._is_true(

            filter_result,

            "adx_ok",

        )


        atr_ok = self._is_true(

            filter_result,

            "atr_ok",

        )


        # ==================================================
        # COMPATIBILITY FALLBACK
        #
        # Allows older strategies to work until all engines
        # are connected to the new SignalFilter.
        # ==================================================

        if not filter_result:

            ema_structure_ok = bool(

                features.get(

                    "trend_ok",

                    False,

                )

                or

                features.get(

                    "ema_ok",

                    False,

                )

            )


            ema_slope_ok = bool(

                features.get(

                    "ema_slope_ok",

                    False,

                )

            )


            price_position_ok = bool(

                features.get(

                    "price_position_ok",

                    False,

                )

            )


            rsi_direction_ok = bool(

                features.get(

                    "rsi_ok",

                    False,

                )

            )


            macd_direction_ok = bool(

                features.get(

                    "macd_ok",

                    False,

                )

            )


            adx_ok = bool(

                features.get(

                    "adx_ok",

                    False,

                )

            )


            atr_ok = bool(

                features.get(

                    "atr_ok",

                    True,

                )

            )


        # ==================================================
        # UNIVERSAL SCORE
        # ==================================================

        universal_checks = (

            (

                "EMA_STRUCTURE",

                ema_structure_ok,

                self.weights["ema_structure"],

            ),

            (

                "EMA_SLOPE",

                ema_slope_ok,

                self.weights["ema_slope"],

            ),

            (

                "PRICE_POSITION",

                price_position_ok,

                self.weights["price_position"],

            ),

            (

                "RSI_DIRECTION",

                rsi_direction_ok,

                self.weights["rsi_direction"],

            ),

            (

                "MACD_DIRECTION",

                macd_direction_ok,

                self.weights["macd_direction"],

            ),

            (

                "ADX_STRENGTH",

                adx_ok,

                self.weights["adx_strength"],

            ),

            (

                "ATR_SAFETY",

                atr_ok,

                self.weights["atr_safety"],

            ),

        )


        for (

            factor_name,

            condition,

            weight,

        ) in universal_checks:

            if condition:

                score += weight

                passed_factors.append(

                    factor_name

                )

            else:

                failed_factors.append(

                    factor_name

                )


        # ==================================================
        # STRATEGY-SPECIFIC OPTIONAL BONUS
        # ==================================================

        (

            primary_event,

            secondary_event,

        ) = self._classify_strategy_event(

            signal,

            features,

        )


        special_confirmation = (

            self._has_special_confirmation(

                features

            )

        )


        if primary_event:

            score += self.weights[

                "strategy_primary_event"

            ]

            passed_factors.append(

                "STRATEGY_PRIMARY_EVENT"

            )


        if secondary_event:

            score += self.weights[

                "strategy_secondary_event"

            ]

            passed_factors.append(

                "STRATEGY_SECONDARY_EVENT"

            )


        if special_confirmation:

            score += self.weights[

                "strategy_special_confirmation"

            ]

            passed_factors.append(

                "STRATEGY_SPECIAL_CONFIRMATION"

            )


        # ==================================================
        # SCORE LIMIT
        # ==================================================

        score = min(

            int(score),

            100,

        )


        quality_class = self._quality_class(

            score

        )


        # ==================================================
        # EXECUTION RECOMMENDATION
        #
        # This is descriptive only.
        # Actual rejection should remain in SignalFilter
        # or the execution routing layer.
        # ==================================================

        score_passed = (

            score >= 55

            and

            direction_quality_ok

        )


        # ==================================================
        # STORE SCORE DETAILS IN SIGNAL
        # ==================================================

        signal["score"] = score

        signal["quality_class"] = quality_class

        signal["score_passed"] = score_passed


        signal["score_details"] = {

            "direction": direction,

            "score": score,

            "quality_class": quality_class,

            "score_passed": score_passed,

            "direction_quality_ok": (

                direction_quality_ok

            ),

            "filter_quality_score": (

                filter_quality_score

            ),

            "passed_factors": passed_factors,

            "failed_factors": failed_factors,

            "primary_event": primary_event,

            "secondary_event": secondary_event,

            "special_confirmation": (

                special_confirmation

            ),

        }


        # ==================================================
        # DEBUG REPORT
        # ==================================================

        print(

            "QUALITY SCORE :",

            score,

            "| CLASS :",

            quality_class,

            "| DIRECTION :",

            direction,

            "| FILTER SCORE :",

            filter_quality_score,

            "| PASSED :",

            score_passed,

        )


        return score