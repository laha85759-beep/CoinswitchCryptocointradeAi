import re

path = 'c:/Users/karth/Downloads/CoinswitchCryptocointradeAi-main/CoinswitchCryptocointradeAi-main/institutional_strategy_matrix.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Volume Profile and Order Flow Delta methods
indicators_code = '''        return cum_vp / (cum_vol + 1e-9)

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, bins: int = 24) -> Dict[str, Any]:
        """
        Computes Institutional Volume Profile:
        - Point of Control (POC): Price level with highest traded volume
        - Value Area High (VAH) and Value Area Low (VAL): 70% of total volume
        """
        if len(df) < 5 or "volume" not in df.columns or df["volume"].sum() <= 0:
            p = float(df["close"].iloc[-1])
            return {"poc": p, "vah": p * 1.01, "val": p * 0.99, "in_value_area": True, "below_val": False, "above_vah": False}
        
        price_min = float(df["low"].min())
        price_max = float(df["high"].max())
        if price_max <= price_min:
            p = float(df["close"].iloc[-1])
            return {"poc": p, "vah": p * 1.01, "val": p * 0.99, "in_value_area": True, "below_val": False, "above_vah": False}

        bin_size = (price_max - price_min) / bins
        vol_bins = np.zeros(bins)
        
        typical_prices = (df["high"] + df["low"] + df["close"]) / 3.0
        for tp, v in zip(typical_prices, df["volume"]):
            idx = int((tp - price_min) / bin_size)
            idx = min(max(idx, 0), bins - 1)
            vol_bins[idx] += v

        poc_idx = int(np.argmax(vol_bins))
        poc_price = price_min + (poc_idx + 0.5) * bin_size

        total_vol = np.sum(vol_bins)
        target_vol = total_vol * 0.70
        curr_vol = vol_bins[poc_idx]
        left_idx, right_idx = poc_idx, poc_idx

        while curr_vol < target_vol and (left_idx > 0 or right_idx < bins - 1):
            next_left_vol = vol_bins[left_idx - 1] if left_idx > 0 else 0
            next_right_vol = vol_bins[right_idx + 1] if right_idx < bins - 1 else 0
            if next_left_vol >= next_right_vol and left_idx > 0:
                left_idx -= 1
                curr_vol += next_left_vol
            elif right_idx < bins - 1:
                right_idx += 1
                curr_vol += next_right_vol
            else:
                break

        val_price = price_min + left_idx * bin_size
        vah_price = price_min + (right_idx + 1) * bin_size
        curr_price = float(df["close"].iloc[-1])

        return {
            "poc": round(poc_price, 6),
            "vah": round(vah_price, 6),
            "val": round(val_price, 6),
            "in_value_area": val_price <= curr_price <= vah_price,
            "above_vah": curr_price > vah_price,
            "below_val": curr_price < val_price
        }

    @staticmethod
    def calculate_order_flow_delta(df: pd.DataFrame, lookback: int = 5) -> Dict[str, Any]:
        """
        Calculates Order Flow Imbalance, Cumulative Volume Delta (CVD), and Aggressive Volume Pressure.
        """
        if len(df) < lookback:
            return {"net_delta_ratio": 0.0, "bias": "neutral", "absorption": False}
        
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        deltas = []
        for k in range(-lookback, 0):
            rng = max(high[k] - low[k], 1e-6)
            buy_vol = volume[k] * ((close[k] - low[k]) / rng)
            sell_vol = volume[k] * ((high[k] - close[k]) / rng)
            deltas.append(buy_vol - sell_vol)

        net_delta = float(np.sum(deltas))
        tot_vol = float(np.sum(volume[-lookback:])) or 1.0
        delta_ratio = round(net_delta / tot_vol, 3)

        price_diff = close[-1] - close[-lookback]
        absorption = False
        bias = "neutral"

        if price_diff < 0 and delta_ratio > 0.10:
            absorption = True
            bias = "bullish"
        elif price_diff > 0 and delta_ratio < -0.10:
            absorption = True
            bias = "bearish"
        elif delta_ratio > 0.15:
            bias = "bullish"
        elif delta_ratio < -0.15:
            bias = "bearish"

        return {
            "net_delta_ratio": delta_ratio,
            "bias": bias,
            "absorption": absorption
        }
'''

content = content.replace('        return cum_vp / (cum_vol + 1e-9)', indicators_code, 1)

# 2. Add Strategy 0: Core Order Flow + Volume Profile (POC/VAH/VAL) + VWAP + EMA 43
core_strat_code = '''
    # ── 3. STRATEGY DEFINITIONS ──────────────────────────────────────────

    def eval_strategy_0_core_orderflow_vp_vwap_ema43(
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

            # Volume Profile confirmation: bouncing off VAL or breaking above POC/VAH
            if close >= vp["poc"] or vp["below_val"] is False:
                long_points += 20
                confluence_reasons.append(f"Volume Profile Support (POC: {vp['poc']})")

            # Order Flow confirmation: positive CVD delta or aggressive absorption of sellers
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

            # Volume Profile confirmation: rejecting VAH or trading below POC
            if close <= vp["poc"] or vp["above_vah"] is False:
                short_points += 20
                confluence_reasons.append(f"Volume Profile Resistance (POC: {vp['poc']})")

            # Order Flow confirmation: negative CVD delta or aggressive absorption of buyers
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
'''

content = content.replace('    # ── 3. STRATEGY DEFINITIONS ──────────────────────────────────────────', core_strat_code, 1)

# 3. Insert eval_strategy_0 as the FIRST priority in strategies_to_test
old_test_list = '''        strategies_to_test = [
            lambda: self.eval_strategy_10_multi_timeframe(df_m5, df_m15 or df_m5, df_h1 or df_m5),'''

new_test_list = '''        strategies_to_test = [
            lambda: self.eval_strategy_0_core_orderflow_vp_vwap_ema43(df_m5, df_h1),
            lambda: self.eval_strategy_10_multi_timeframe(df_m5, df_m15 or df_m5, df_h1 or df_m5),'''

content = content.replace(old_test_list, new_test_list, 1)

# 4. Fix calculate_trade_parameters to use percentage for low-priced altcoins instead of flat 0.5 dollar
old_calc_params = '''        if direction == "BUY":
            swing_low = struct.get("prev_swing_low") or (close - buffer)
            sl_price = round(min(close - buffer, swing_low - (atr * 0.3)), 4)
            risk_dist = max(close - sl_price, 0.5)
            tp1 = round(close + (risk_dist * 1.0), 4)
            tp2 = round(close + (risk_dist * 2.0), 4)
            tp3 = round(close + (risk_dist * 3.0), 4)
        else:
            swing_high = struct.get("prev_swing_high") or (close + buffer)
            sl_price = round(max(close + buffer, swing_high + (atr * 0.3)), 4)
            risk_dist = max(sl_price - close, 0.5)
            tp1 = round(close - (risk_dist * 1.0), 4)
            tp2 = round(close - (risk_dist * 2.0), 4)
            tp3 = round(close - (risk_dist * 3.0), 4)'''

new_calc_params = '''        # Dynamic minimum risk distance: 0.8% of price or ATR (avoids giant $0.50 SL on sub-dollar coins)
        min_risk_dist = max(close * 0.008, 1e-6)

        if direction == "BUY":
            swing_low = struct.get("prev_swing_low") or (close - buffer)
            raw_sl = min(close - buffer, swing_low - (atr * 0.3))
            risk_dist = max(close - raw_sl, min_risk_dist)
            sl_price = round(close - risk_dist, 6)
            tp1 = round(close + (risk_dist * 1.5), 6)
            tp2 = round(close + (risk_dist * 3.0), 6)
            tp3 = round(close + (risk_dist * 4.5), 6)
        else:
            swing_high = struct.get("prev_swing_high") or (close + buffer)
            raw_sl = max(close + buffer, swing_high + (atr * 0.3))
            risk_dist = max(raw_sl - close, min_risk_dist)
            sl_price = round(close + risk_dist, 6)
            tp1 = round(close - (risk_dist * 1.5), 6)
            tp2 = round(close - (risk_dist * 3.0), 6)
            tp3 = round(close - (risk_dist * 4.5), 6)'''

content = content.replace(old_calc_params, new_calc_params, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated institutional_strategy_matrix.py successfully!')
