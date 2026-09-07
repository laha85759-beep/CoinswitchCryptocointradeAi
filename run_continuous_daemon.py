"""
CoinsAI Continuous 24/7 Always-On Daemon Runner
===============================================
Runs main.py in a continuous infinite loop every 60 seconds.
Automatically syncs live exchange positions, purges stale records,
monitors active positions, ratchets trailing stops, and executes breakout trades!
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
print("     STARTING COINSAI 24/7 ALWAYS-ON CONTINUOUS DAEMON RUNNER     ")
print("==================================================================")
log.info("Continuous Daemon Runner started. Polling every 60 seconds 24/7...")

cycle_count = 0

while True:
    try:
        cycle_count += 1
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log.info(f"--- STARTING DAEMON CYCLE #{cycle_count} AT {now_str} ---")
        
        # Execute main trading & monitoring pipeline
        run()
        
        log.info(f"--- CYCLE #{cycle_count} COMPLETE. SLEEPING 60 SECONDS ---")
    except KeyboardInterrupt:
        log.info("Daemon interrupted by user. Stopping cleanly...")
        break
    except Exception as exc:
        log.error(f"Daemon cycle #{cycle_count} encountered error: {exc}", exc_info=True)
    
    time.sleep(60)
