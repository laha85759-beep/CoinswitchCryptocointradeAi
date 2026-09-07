"""
CoinsAI Continuous 24/7 Always-On Daemon Runner
===============================================
Runs main.py in an active 24/7 continuous real-time execution loop.
Instantly syncs live exchange positions, ratchets trailing stops (+0.2%),
scans 250+ spot & futures pairs, and executes breakout trades without sleeping!
"""

import logging
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, ".")
from main import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daemon.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("CONTINUOUS_DAEMON")

print("==================================================================")
print("     STARTING OPUS 4.7 REAL-TIME CONTINUOUS DAEMON (ZERO SLEEP)   ")
print("==================================================================")
log.info("Continuous Active Daemon Runner started. Scanning real-time 24/7 without delay...")

cycle_count = 0

while True:
    try:
        cycle_count += 1
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log.info(f"--- STARTING REAL-TIME DAEMON CYCLE #{cycle_count} AT {now_str} ---")
        
        # Execute main trading & monitoring pipeline
        run()
        
        log.info(f"--- DAEMON CYCLE #{cycle_count} COMPLETE. RE-SCANNING INSTANTLY ---")
    except KeyboardInterrupt:
        log.info("Daemon interrupted by user. Stopping cleanly...")
        break
    except Exception as exc:
        log.error(f"Daemon cycle #{cycle_count} encountered error: {exc}", exc_info=True)
    
    # 1-second tick to yield control to event loop & avoid tight CPU loop
    time.sleep(1)
