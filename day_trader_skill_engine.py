import os
import sys

# Ensure day-trader-skill is accessible
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pass

class DayTraderSkillEngine:
    """
    Day Trader Skill Confluence Engine:
    Adapts algorithms from 'day-trader-skill':
      1. trader-entry: Opening Range Breakout (ORB) & VWAP intraday filter
      2. trader-exit: Risk:Reward target calculation (2R standard, min 1:1.5)
      3. trader-risk: Account risk cap & volatility guard
      4. trader-timemachine: Fast session Monte Carlo simulation for probability of success
    """
    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    def calculate_vwap(self, df):
        """Calculates Volume Weighted Average Price (VWAP) across bars."""
        try:
            if df is None or len(df) < 5:
                return None
            v = df['volume']
            tp = (df['high'] + df['low'] + df['close']) / 3.0
            cum_vol = v.cumsum()
            cum_vp = (tp * v).cumsum()
            vwap = cum_vp / cum_vol.replace(0, np.nan)
            return vwap.iloc[-1]
        except Exception:
            return None

    def evaluate_entry_timing(self, df, current_price, signal_type="pump"):
        """
        trader-entry check:
        For long ('pump'):
          - Price should ideally be above VWAP (institutional buyers control).
          - Check if price broke above the recent 15-bar opening range high (ORB).
        For short ('dump'):
          - Price should be below VWAP.
        """
        try:
            if df is None or len(df) < 15:
                return {"pass": True, "reason": "insufficient_bars_bypass"}

            vwap = self.calculate_vwap(df)
            recent_high = df['high'].iloc[-15:-1].max()
            recent_low = df['low'].iloc[-15:-1].min()

            if signal_type == "pump":
                above_vwap = current_price >= vwap if vwap else True
                orb_break = current_price >= recent_high * 0.998  # near or breaking 15-bar high
                passed = above_vwap or orb_break
                return {
                    "pass": passed,
                    "vwap": round(float(vwap), 6) if vwap else None,
                    "or_high": round(float(recent_high), 6),
                    "or_low": round(float(recent_low), 6),
                    "above_vwap": above_vwap,
                    "orb_break": orb_break,
                    "reason": "orb_vwap_bullish" if passed else "price_below_vwap_and_or_high"
                }
            else:
                below_vwap = current_price <= vwap if vwap else True
                passed = below_vwap
                return {
                    "pass": passed,
                    "vwap": round(float(vwap), 6) if vwap else None,
                    "below_vwap": below_vwap,
                    "reason": "vwap_bearish" if passed else "price_above_vwap"
                }
        except Exception as e:
            return {"pass": True, "reason": f"entry_eval_err: {str(e)}"}

    def run_monte_carlo_timemachine(self, df, entry_price, sl_price, tp_price, replays=1000):
        """
        trader-timemachine simulation:
        Simulate 1,000 forward paths from bar return distributions.
        Calculates the probability of reaching Target before Stop.
        """
        try:
            if df is None or len(df) < 20 or entry_price <= 0:
                return {"win_rate": 0.75, "reason": "default_pass_sparse_data"}

            # Log returns from close-to-close
            returns = (df['close'] / df['close'].shift(1) - 1.0).dropna().values
            if len(returns) < 10:
                return {"win_rate": 0.70, "reason": "few_returns"}

            # Standard deviation & mean return per bar
            mu = np.mean(returns)
            sigma = np.std(returns)
            if sigma == 0:
                sigma = 0.005

            is_long = tp_price > entry_price
            steps = 40  # simulate next 40 bars (~3 hours on 5m)

            wins = 0
            losses = 0

            # Vectorized Monte Carlo Simulation
            random_shocks = np.random.normal(loc=mu, scale=sigma, size=(replays, steps))
            price_paths = entry_price * np.cumprod(1.0 + random_shocks, axis=1)

            for path in price_paths:
                hit_tp = False
                hit_sl = False
                for p in path:
                    if is_long:
                        if p <= sl_price:
                            hit_sl = True
                            break
                        elif p >= tp_price:
                            hit_tp = True
                            break
                    else:
                        if p >= sl_price:
                            hit_sl = True
                            break
                        elif p <= tp_price:
                            hit_tp = True
                            break
                if hit_tp:
                    wins += 1
                elif hit_sl:
                    losses += 1
                else:
                    # Neither touched within 40 bars; check if in profit
                    final_p = path[-1]
                    if (is_long and final_p > entry_price) or (not is_long and final_p < entry_price):
                        wins += 1
                    else:
                        losses += 1

            sim_win_rate = wins / float(replays)
            return {
                "win_rate": round(sim_win_rate, 4),
                "replays": replays,
                "passed": sim_win_rate >= 0.52,  # Require positive statistical edge
                "reason": f"monte_carlo_edge_{sim_win_rate*100:.1f}pct"
            }
        except Exception as e:
            return {"win_rate": 0.70, "passed": True, "reason": f"sim_err: {str(e)}"}

    def plan_exits(self, entry_price, direction="long", atr=None):
        """
        trader-exit plan:
        Enforce minimum 1:2.0 Risk:Reward ratio.
        """
        try:
            if entry_price <= 0:
                return None, None
            
            risk_dist = (atr * 1.5) if (atr and atr > 0) else (entry_price * 0.015)
            # Minimum 0.5% risk distance
            risk_dist = max(risk_dist, entry_price * 0.005)

            if direction == "long":
                sl = entry_price - risk_dist
                tp = entry_price + (risk_dist * 2.0)  # 2R target
            else:
                sl = entry_price + risk_dist
                tp = entry_price - (risk_dist * 2.0)

            return round(float(sl), 6), round(float(tp), 6)
        except Exception:
            return None, None
