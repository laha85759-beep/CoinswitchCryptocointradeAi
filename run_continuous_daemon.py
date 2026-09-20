"""
CoinsAI Continuous 24/7 Always-On Daemon Runner (Low-Memory Edition)
=====================================================================
Runs main.py in an active 24/7 continuous real-time execution loop.
Optimized for 512MB RAM on Render:
- Automatic garbage collection (gc.collect())
- Glibc memory trimming (malloc_trim)
- 15-second scan cadence to prevent tight-loop memory accumulation
"""

import gc
import ctypes
import logging
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, ".")
from main import run

# Force garbage collector thresholds to be tight
gc.set_threshold(400, 5, 5)

def trim_memory():
    gc.collect()
    try:
        # Release unmapped virtual memory back to Linux kernel
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daemon.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("CONTINUOUS_DAEMON")

if __name__ == "__main__":
    print("==================================================================")
    print("     STARTING COINSAI 24/7 ULTRA-LOW-MEMORY DAEMON ENGINE        ")
    print("==================================================================")
    log.info("Continuous Active Daemon Runner started. Memory watchdog active.")

    cycle_count = 0

    while True:
        try:
            cycle_count += 1
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log.info(f"--- STARTING DAEMON CYCLE #{cycle_count} AT {now_str} ---")
            
            # Execute main trading & monitoring pipeline
            run()
            
            # Clean memory immediately after every cycle
            trim_memory()
            log.info(f"--- DAEMON CYCLE #{cycle_count} COMPLETE. MEMORY TRIMMED ---")
        except KeyboardInterrupt:
            log.info("Daemon interrupted by user. Stopping cleanly...")
            break
        except Exception as exc:
            log.error(f"Daemon cycle #{cycle_count} encountered error: {exc}", exc_info=True)
            trim_memory()
        
        # 15-second cadence between scan cycles:
        # 1. Gives exchange APIs breathing room (prevents 429 rate limits)
        # 2. Allows Linux kernel to reclaim RAM freed by trim_memory()
        # 3. Keeps position trailing and breakout detection completely up-to-date
        time.sleep(15)
