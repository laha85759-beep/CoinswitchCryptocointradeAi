path = 'c:/Users/karth/Downloads/CoinswitchCryptocointradeAi-main/CoinswitchCryptocointradeAi-main/institutional_strategy_matrix.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '    def eval_strategy_1_structure_vwap(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:'

strategy_0_impl = '''    def eval_strategy_0_core_orderflow_vp_vwap_ema43(
        self, df_m5: pd.DataFrame, df_h1: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        MASTER CORE STRATEGY: Order Flow + Volume Profile + VWAP + EMA 43 Trend Filter.
        Requires strict confluence:
          1. EMA 43: Price > EMA 43 (BULLISH) or Price < EMA 43 (BEARISH)
          2. VWAP: Price > Session VWAP for longs, Price < Session VWAP for shorts
          3. Volume Profile: Entry relative to Value Area (VAH/VAL bounce or POC acceptance)
          4. Order Flow / CVD: Aggressive buyer/seller delta confirming trade direction (>0.10 or absorption)
        """
        if len(df_m5) < 45:
            return {"name": "Core OrderFlow + VP + VWAP + EMA 43", "score": 0, "approved": False, "reason": "insufficient_candles"}

        close = float(df_m5["close"].iloc[-1])
        ema43 = float(self.calculate_ema(df_m5["close"], 43).iloc[-1])
        vwap = float(self.calculate_session_vwap(df_m5).iloc[-1])
        vp = self.calculate_volume_profile(df_m5)
        of = self.calculate_order_flow_delta(df_m5)

        score = 0
        direction = None
        confluence_reasons = []

        # --- LONG CONFLUENCE ---
        if close > ema43 and close > vwap:
            long_points = 50
            confluence_reasons.append("Price > EMA 43 and VWAP")

            if close >= vp["poc"] or vp.get("below_val", False) is False:
                long_points += 20
                confluence_reasons.append(f"Volume Profile Support (POC: {vp['poc']})")

            if of["bias"] == "bullish" or of["absorption"]:
                long_points += 25
                confluence_reasons.append(f"Order Flow Bullish Delta: {of['net_delta_ratio']}")

            if long_points >= 85:
                score = long_points
                direction = "BUY"

        # --- SHORT CONFLUENCE ---
        elif close < ema43 and close < vwap:
            short_points = 50
            confluence_reasons.append("Price < EMA 43 and VWAP")

            if close <= vp["poc"] or vp.get("above_vah", False) is False:
                short_points += 20
                confluence_reasons.append(f"Volume Profile Resistance (POC: {vp['poc']})")

            if of["bias"] == "bearish" or of["absorption"]:
                short_points += 25
                confluence_reasons.append(f"Order Flow Bearish Delta: {of['net_delta_ratio']}")

            if short_points >= 85:
                score = short_points
                direction = "SELL"

        return {
            "name": "Core OrderFlow + VP + VWAP + EMA 43",
            "score": score,
            "direction": direction,
            "approved": score >= self.min_quality_score,
            "ema43": round(ema43, 6),
            "vwap": round(vwap, 6),
            "poc": vp["poc"],
            "vah": vp["vah"],
            "val": vp["val"],
            "order_flow_delta": of["net_delta_ratio"],
            "confluence": " | ".join(confluence_reasons)
        }

    def eval_strategy_1_structure_vwap(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:'''

if target in content:
    content = content.replace(target, strategy_0_impl, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected eval_strategy_0_core_orderflow_vp_vwap_ema43 into InstitutionalStrategyEngine!")
else:
    print("Target not found!")
