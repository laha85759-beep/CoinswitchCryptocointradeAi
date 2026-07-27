import argparse
import logging
import os
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from config import CONFIG
from coinswitch_client import CoinSwitchClient
from scanner import SignalEngine, ConsolidationBreakoutEngine
from agents import confidence_score, suspected_cause, synthetic_imbalance, pct_change, risk_reject

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backtest")

DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT",
    "AVAX/USDT", "LINK/USDT", "DOT/USDT", "BNB/USDT", "MATIC/USDT", "UNI/USDT",
    "AAVE/USDT", "NEAR/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "FIL/USDT",
    "INJ/USDT", "SUI/USDT"
]

def fetch_historical_data(client: CoinSwitchClient, symbol: str, months: int) -> pd.DataFrame:
    data_dir = Path("backtest_data")
    data_dir.mkdir(exist_ok=True)
    filename = symbol.replace("/", "_") + "_5m.csv"
    filepath = data_dir / filename
    
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (months * 30 * 24 * 60 * 60 * 1000)
    
    if filepath.exists():
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        first_ts = df.index[0].timestamp() * 1000
        if first_ts <= start_ts + (7 * 24 * 60 * 60 * 1000):
            log.info(f"Loaded {symbol} from cache ({len(df)} rows).")
            return df
        else:
            log.info(f"Cache for {symbol} insufficient. Re-downloading.")

    log.info(f"Downloading historical data for {symbol} ({months} months)...")
    all_candles = []
    current_end = end_ts
    
    pbar = tqdm(total=end_ts - start_ts)
    while current_end > start_ts:
        current_start = max(start_ts, current_end - (120 * 5 * 60 * 1000))
        try:
            resp = client._request(
                "GET", "/trade/api/v2/candles",
                params={
                    "exchange": "c2c2",
                    "symbol": symbol,
                    "interval": "5",
                    "start_time": str(int(current_start)),
                    "end_time": str(int(current_end))
                }
            )
            candles = resp.get("data", [])
            if not candles:
                log.warning(f"No candles returned for {symbol} between {current_start} and {current_end}.")
                break
                
            all_candles.extend(candles)
            
            earliest_candle_time = min(int(c["start_time"]) for c in candles)
            advanced = current_end - earliest_candle_time
            if advanced <= 0:
                break
            
            pbar.update(advanced)
            current_end = earliest_candle_time - 1
            time.sleep(0.3) # rate limit
        except Exception as e:
            log.error(f"Error fetching candles for {symbol}: {e}")
            break
            
    pbar.close()

    if not all_candles:
        log.warning(f"Failed to fetch any data for {symbol}.")
        return pd.DataFrame()

    df = pd.DataFrame(all_candles)
    df = df.drop_duplicates(subset=["start_time"])
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["start_time"]), unit="ms")
    df["open"] = df["o"].astype(float)
    df["high"] = df["h"].astype(float)
    df["low"] = df["l"].astype(float)
    df["close"] = df["c"].astype(float)
    df["volume"] = df["volume"].astype(float)
    
    df = df.set_index("timestamp").sort_index()
    df.to_csv(filepath)
    log.info(f"Saved {symbol} historical data ({len(df)} rows).")
    return df

class Backtester:
    def __init__(self, initial_capital: float, shorts_enabled: bool, months: int, symbols: list[str]):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.shorts_enabled = shorts_enabled
        self.months = months
        self.symbols = symbols
        
        self.open_trades = []
        self.closed_trades = []
        self.equity_curve = []
        self.daily_pnl = {}
        
        self.cfg = CONFIG.copy()
        self.cfg["paper_trading_mode"] = True
        
        self.signal_engine = SignalEngine(self.cfg["weights"])
        self.consol_engine = ConsolidationBreakoutEngine(self.cfg)
        
        self.data = {}
        self.timestamps = []
        
        # Risk configs
        self.taker_fee = 0.001
        self.max_capital_pct = self.cfg.get("max_capital_pct", 40)
        self.max_open_trades = self.cfg.get("max_open_trades", 2)
        self.hard_sl_pct = self.cfg.get("hard_sl_pct", 1.5)
        self.trail_activation_pct = self.cfg.get("trail_activation_pct", 1.5)
        self.trail_pct = self.cfg.get("trail_pct", 1.0)
        self.take_profit_pct = self.cfg.get("take_profit_pct", 4.0)

    def load_data(self, client: CoinSwitchClient):
        master_idx = None
        for sym in self.symbols:
            df = fetch_historical_data(client, sym, self.months)
            if not df.empty:
                self.data[sym] = df
                if master_idx is None:
                    master_idx = df.index
                else:
                    master_idx = master_idx.union(df.index)
        
        if master_idx is not None:
            self.timestamps = sorted([ts for ts in master_idx])
        else:
            self.timestamps = []

    def classify_signal(self, item: dict) -> dict:
        symbol = item.get("symbol")
        consol = item.get("consolidation_breakout")
        if consol:
            strength = consol.get("strength", 0)
            confidence = min(1.0, 0.55 + strength / 300)
            if confidence >= self.cfg.get("consolidation_breakout_score_min", 0.55):
                return self._format_signal(symbol, "pump", confidence, consol.get("type", "consolidation_breakout"), item)

        up_move = item["change_5m"] > self.cfg["pump_change_5m_pct"] or item["change_1h"] > self.cfg["pump_change_1h_pct"]
        down_move = item["change_5m"] < -self.cfg["dump_change_5m_pct"] or item["change_1h"] < -self.cfg["dump_change_1h_pct"]
        high_vol = item["volume_zscore"] > self.cfg["volume_zscore_min"]
        buy_dom = item["orderbook_imbalance"] > self.cfg["buy_imbalance_min"]
        sell_dom = item["orderbook_imbalance"] < (1.0 - self.cfg["sell_imbalance_min"])
        trade_spike = item.get("trade_freq_ratio", 0) >= self.cfg["trade_frequency_spike_ratio"]

        trend_up = item.get("change_4h", 0) > 0
        trend_down = item.get("change_4h", 0) < 0

        pump_count = sum([up_move, high_vol, buy_dom, trade_spike])
        dump_count = sum([down_move, high_vol, sell_dom, trade_spike])

        signal = "normal"
        if pump_count >= 3 or (pump_count >= 2 and trend_up):
            signal = "pump"
        elif dump_count >= 3 or (dump_count >= 2 and trend_down):
            signal = "dump"
        elif max(pump_count, dump_count) >= self.cfg["watch_condition_count"]:
            signal = "watch"

        conf = confidence_score(item, pump_count if signal != "dump" else dump_count, trend_up if signal != "dump" else trend_down)
        cause = suspected_cause(item, high_vol, trade_spike)
        return self._format_signal(symbol, signal, conf, cause, item)

    def _format_signal(self, symbol: str, signal: str, confidence: float, cause: str, item: dict) -> dict:
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "suspected_cause": cause,
            "supporting_data": item,
            "timestamp": item.get("timestamp")
        }

    def evaluate_risk(self, signal: dict, current_ts: pd.Timestamp) -> dict:
        symbol = signal["symbol"]
        
        if signal["signal"] not in ("pump", "dump"):
            return None
            
        if signal["signal"] == "dump" and not self.shorts_enabled:
            return None

        if signal["confidence"] < self.cfg["min_confidence"]:
            return None

        # Check existing trades
        if any(t["symbol"] == symbol for t in self.open_trades):
            return None
        
        if len(self.open_trades) >= self.max_open_trades:
            return None
            
        # Daily drawdown check
        date_str = current_ts.date().isoformat()
        day_loss = self.daily_pnl.get(date_str, 0)
        max_drawdown = self.capital * self.cfg["daily_max_drawdown_pct"] / 100.0
        if day_loss < -max_drawdown:
            return None
            
        position_size = self.capital * (self.max_capital_pct / 100.0)
        if position_size < self.cfg.get("min_order_usdt", 1.0):
            return None

        return {
            "symbol": symbol,
            "approved": True,
            "position_size_usd": position_size,
            "stop_loss_pct": self.hard_sl_pct,
            "take_profit_pct": self.take_profit_pct,
            "direction": "long" if signal["signal"] == "pump" else "short",
            "signal": signal,
            "entry_price": signal["supporting_data"]["price"]
        }

    def execute_trade(self, approval: dict, current_ts: pd.Timestamp):
        symbol = approval["symbol"]
        entry_price = approval["entry_price"]
        size = approval["position_size_usd"]
        
        # Apply entry fee
        fee = size * self.taker_fee
        self.capital -= fee
        
        direction = approval["direction"]
        if direction == "long":
            hard_sl = entry_price * (1 - approval["stop_loss_pct"] / 100.0)
            tp = entry_price * (1 + approval["take_profit_pct"] / 100.0)
        else:
            hard_sl = entry_price * (1 + approval["stop_loss_pct"] / 100.0)
            tp = entry_price * (1 - approval["take_profit_pct"] / 100.0)
            
        self.open_trades.append({
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "qty": size / entry_price,
            "usdt_used": size,
            "hard_sl": hard_sl,
            "take_profit": tp,
            "peak_price": entry_price,
            "trail_active": False,
            "trailing_stop": None,
            "opened_at": current_ts,
            "highest_profit_pct": 0.0
        })

    def run(self):
        log.info(f"Starting backtest with {len(self.timestamps)} steps. Initial capital: ${self.capital}")
        
        # We need at least 120 candles history to start. Skip the first 120 timestamps.
        if len(self.timestamps) < 120:
            log.error("Not enough data to run backtest.")
            return
            
        start_idx = 120
        # step by 15m (which is 3 * 5m candles)
        for i in tqdm(range(start_idx, len(self.timestamps), 3)):
            ts = self.timestamps[i]
            
            # 1. Update Open Trades using Intra-bar High/Low since last check
            # For a 15m step, we look at the candles between i-2 and i.
            # We simplify by just checking the current candle (i) for simplicity in standard backtesting, 
            # or check the slice for more accurate intra-bar.
            for trade in list(self.open_trades):
                symbol = trade["symbol"]
                df = self.data.get(symbol)
                if df is None: continue
                
                try:
                    # Get the current candle
                    idx_loc = df.index.get_indexer([ts], method='ffill')[0]
                    if idx_loc == -1: continue
                    candle = df.iloc[idx_loc]
                    
                    high, low, close = candle.high, candle.low, candle.close
                    
                    # Calculate current PnL pct based on high/low for peak
                    if trade["direction"] == "long":
                        peak_pnl = pct_change(high, trade["entry_price"])
                        close_pnl = pct_change(close, trade["entry_price"])
                        low_pnl = pct_change(low, trade["entry_price"])
                        
                        if high > trade["peak_price"]:
                            trade["peak_price"] = high
                            
                    else:
                        # short
                        peak_pnl = pct_change(trade["entry_price"], low)
                        close_pnl = pct_change(trade["entry_price"], close)
                        high_pnl = pct_change(trade["entry_price"], high)
                        
                        if low < trade["peak_price"]:
                            trade["peak_price"] = low
                            
                    trade["highest_profit_pct"] = max(trade["highest_profit_pct"], peak_pnl)
                    
                    # Activate trail
                    if not trade["trail_active"] and peak_pnl >= self.trail_activation_pct:
                        trade["trail_active"] = True
                        
                    # Update trailing stop
                    if trade["trail_active"]:
                        if trade["direction"] == "long":
                            trade["trailing_stop"] = trade["peak_price"] * (1 - self.trail_pct / 100.0)
                        else:
                            trade["trailing_stop"] = trade["peak_price"] * (1 + self.trail_pct / 100.0)
                            
                    active_stop = trade.get("trailing_stop") or trade["hard_sl"]
                    
                    close_reason = None
                    exit_price = 0
                    
                    # Check stops/TP
                    if trade["direction"] == "long":
                        if low <= active_stop:
                            close_reason = "trailing_stop" if trade["trail_active"] else "stop_loss"
                            exit_price = active_stop
                        elif high >= trade["take_profit"]:
                            close_reason = "take_profit"
                            exit_price = trade["take_profit"]
                    else:
                        if high >= active_stop:
                            close_reason = "trailing_stop" if trade["trail_active"] else "stop_loss"
                            exit_price = active_stop
                        elif low <= trade["take_profit"]:
                            close_reason = "take_profit"
                            exit_price = trade["take_profit"]
                            
                    if close_reason:
                        # Close trade
                        pnl_pct = pct_change(exit_price, trade["entry_price"]) if trade["direction"] == "long" else pct_change(trade["entry_price"], exit_price)
                        gross_pnl_usd = (pnl_pct / 100.0) * trade["usdt_used"]
                        fee = trade["qty"] * exit_price * self.taker_fee
                        net_pnl_usd = gross_pnl_usd - fee
                        
                        self.capital += net_pnl_usd
                        
                        date_str = ts.date().isoformat()
                        self.daily_pnl[date_str] = self.daily_pnl.get(date_str, 0) + net_pnl_usd
                        
                        self.closed_trades.append({
                            "symbol": trade["symbol"],
                            "direction": trade["direction"],
                            "entry_time": trade["opened_at"],
                            "exit_time": ts,
                            "entry_price": trade["entry_price"],
                            "exit_price": exit_price,
                            "reason": close_reason,
                            "pnl_pct": pnl_pct,
                            "net_pnl_usd": net_pnl_usd,
                        })
                        self.open_trades.remove(trade)

                except Exception as e:
                    pass

            # 2. Evaluate new signals if we have room
            if len(self.open_trades) < self.max_open_trades:
                items = []
                for sym in self.symbols:
                    df = self.data.get(sym)
                    if df is None: continue
                    
                    idx_loc = df.index.get_indexer([ts], method='ffill')[0]
                    if idx_loc < 120: continue
                    
                    # Extract 120-candle window
                    window = df.iloc[idx_loc-119:idx_loc+1]
                    
                    close = window["close"].astype(float)
                    high = window["high"].astype(float)
                    low = window["low"].astype(float)
                    volume = window["volume"].astype(float)
                    price = close.iloc[-1]
                    
                    change_5m = pct_change(close.iloc[-1], close.iloc[-2])
                    change_1h = pct_change(close.iloc[-1], close.iloc[-13]) if len(close) >= 13 else 0.0
                    change_4h = pct_change(close.iloc[-1], close.iloc[-49]) if len(close) >= 49 else 0.0
                    change_24h = pct_change(close.iloc[-1], close.iloc[-1 - min(len(close) - 1, 288)])
                    
                    vol_window = volume.tail(84)
                    vol_mean = float(vol_window.mean() or 0)
                    vol_std = float(vol_window.std() or 0)
                    volume_zscore = 0.0 if vol_std <= 0 else float((volume.iloc[-1] - vol_mean) / vol_std)
                    
                    rolling_avg = float(volume.tail(20).mean() or 0)
                    volume_ratio = 1.0 if rolling_avg <= 0 else float(volume.iloc[-1] / rolling_avg)
                    
                    tr = pd.concat([
                        high - low,
                        (high - close.shift(1)).abs(),
                        (low - close.shift(1)).abs()
                    ], axis=1).max(axis=1)
                    atr = float(tr.ewm(span=14, adjust=False).mean().iloc[-1])
                    atr_pct = (atr / price * 100) if price > 0 else 0.0
                    
                    item = {
                        "symbol": sym,
                        "price": price,
                        "change_5m": change_5m,
                        "change_1h": change_1h,
                        "change_4h": change_4h,
                        "change_24h": change_24h,
                        "volume_zscore": volume_zscore,
                        "volume_ratio": volume_ratio,
                        "atr_pct": atr_pct,
                        "orderbook_imbalance": synthetic_imbalance(change_5m, volume_ratio),
                        "trade_freq_ratio": volume_ratio,
                        "timestamp": ts,
                    }
                    
                    # add consolidation check
                    if len(window) >= 48:
                        # resample to 1h for consolidation engine
                        df_1h = window.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
                        if len(df_1h) >= 24:
                            consol = self.consol_engine.detect(df_1h, window)
                            if consol:
                                item["consolidation_breakout"] = consol

                    items.append(item)
                
                # Classify
                signals = [self.classify_signal(i) for i in items]
                signals = [s for s in signals if s is not None]
                
                # Evaluate Risk & Execute
                for sig in signals:
                    approval = self.evaluate_risk(sig, ts)
                    if approval:
                        self.execute_trade(approval, ts)
                        if len(self.open_trades) >= self.max_open_trades:
                            break
                            
            # End of step, record equity
            self.equity_curve.append({"timestamp": ts, "equity": self.capital})

    def report(self):
        log.info("Generating report...")
        
        if self.closed_trades:
            trades_df = pd.DataFrame(self.closed_trades)
            trades_df.to_csv("backtest_trades.csv", index=False)
            
            wins = trades_df[trades_df["net_pnl_usd"] > 0]
            losses = trades_df[trades_df["net_pnl_usd"] <= 0]
            
            win_rate = len(wins) / len(trades_df) * 100
            avg_win = wins["pnl_pct"].mean() if not wins.empty else 0
            avg_loss = losses["pnl_pct"].mean() if not losses.empty else 0
            
            gross_profit = wins["net_pnl_usd"].sum()
            gross_loss = abs(losses["net_pnl_usd"].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            log.info(f"Total Trades: {len(trades_df)}")
            log.info(f"Win Rate: {win_rate:.2f}%")
            log.info(f"Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
            log.info(f"Profit Factor: {profit_factor:.2f}")
            
            # Daily returns for Sharpe Ratio
            if self.equity_curve:
                eq_df = pd.DataFrame(self.equity_curve)
                eq_df.set_index("timestamp", inplace=True)
                # Resample to daily frequency
                daily_eq = eq_df["equity"].resample('D').last().dropna()
                daily_returns = daily_eq.pct_change().dropna()
                if not daily_returns.empty and daily_returns.std() > 0:
                    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
                else:
                    sharpe = 0.0
                log.info(f"Sharpe Ratio: {sharpe:.2f}")
            
            log.info(f"Final Capital: ${self.capital:.2f}")
            log.info(f"Total P&L: ${(self.capital - self.initial_capital):.2f}")
        else:
            log.info("No trades executed.")

        if self.equity_curve:
            eq_df = pd.DataFrame(self.equity_curve)
            eq_df.set_index("timestamp", inplace=True)
            
            # calculate max drawdown
            eq_df["peak"] = eq_df["equity"].cummax()
            eq_df["drawdown"] = (eq_df["equity"] - eq_df["peak"]) / eq_df["peak"] * 100
            max_dd = eq_df["drawdown"].min()
            log.info(f"Max Drawdown: {max_dd:.2f}%")
            
            # plot
            plt.figure(figsize=(12, 6))
            plt.plot(eq_df.index, eq_df["equity"], label="Equity ($)")
            plt.title("Backtest Equity Curve")
            plt.xlabel("Date")
            plt.ylabel("Capital (USD)")
            plt.grid(True)
            plt.legend()
            plt.savefig("backtest_equity.png")
            log.info("Saved equity curve to backtest_equity.png")

def main():
    parser = argparse.ArgumentParser(description="CoinSwitch Bot Backtester")
    parser.add_argument("--capital", type=float, default=1000.0, help="Starting capital (USDT)")
    parser.add_argument("--months", type=int, default=6, help="Months of historical data to fetch")
    parser.add_argument("--shorts", action="store_true", help="Enable short selling (long+short mode)")
    parser.add_argument("--symbols", type=str, default="", help="Comma separated list of symbols (e.g. BTC/USDT,ETH/USDT)")
    parser.add_argument("--min-conf", type=float, default=None, help="Override min_confidence (e.g. 0.50)")
    parser.add_argument("--max-cap", type=float, default=None, help="Override max_capital_pct (e.g. 20)")
    parser.add_argument("--sl", type=float, default=None, help="Override hard_sl_pct (e.g. 2.0)")
    parser.add_argument("--tp", type=float, default=None, help="Override take_profit_pct (e.g. 3.0)")
    
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else DEFAULT_SYMBOLS
    
    client = CoinSwitchClient(CONFIG["api_key"], CONFIG["api_secret"])
    
    backtester = Backtester(
        initial_capital=args.capital,
        shorts_enabled=args.shorts,
        months=args.months,
        symbols=symbols
    )
    
    # Apply CLI overrides
    if args.min_conf is not None:
        backtester.cfg["min_confidence"] = args.min_conf
    if args.max_cap is not None:
        backtester.cfg["max_capital_pct"] = args.max_cap
        backtester.max_capital_pct = args.max_cap
    if args.sl is not None:
        backtester.cfg["hard_sl_pct"] = args.sl
        backtester.hard_sl_pct = args.sl
    if args.tp is not None:
        backtester.cfg["take_profit_pct"] = args.tp
        backtester.take_profit_pct = args.tp
    
    backtester.load_data(client)
    backtester.run()
    backtester.report()

if __name__ == "__main__":
    main()
