"""
CoinsAI Continuous 24/7 Always-On Daemon Runner (Low-Memory Edition)
=====================================================================
Runs main.py in an active 24/7 continuous real-time execution loop.
Optimized for 512MB RAM on Render:
- Automatic garbage collection (gc.collect())
- Glibc memory trimming (malloc_trim) + capped malloc arenas
- 60-second scan cadence: fewer allocations, swing-focused engine
- RSS watchdog: worker self-restarts before the container OOMs
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

# Cap glibc malloc arenas (mirrors webhook_server) so thread pools don't fragment the heap
try:
    import ctypes as _ct
    _libc = _ct.CDLL('libc.so.6')
    _libc.mallopt(-8, 2)  # M_ARENA_MAX = 2
except Exception:
    pass

# ── RSS WATCHDOG: self-restart BEFORE Render's OOM killer does ──────────────
# Render free/starter containers have a hard memory ceiling. When this worker's RSS
# crosses the soft limit it exits cleanly (supervisord restarts it) instead of
# dragging the whole container (web + worker) into the OOM restart email loop.
def _rss_mb() -> float:
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0  # Linux: KB -> MB
    except Exception:
        return 0.0

WORKER_RSS_LIMIT_MB = float(os.getenv('WORKER_RSS_LIMIT_MB', '260'))  # web+worker share 512MB

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
            if _rss_mb() > WORKER_RSS_LIMIT_MB:
                log.warning('RSS watchdog: %.1f MB > %.0f MB limit - restarting worker cleanly', _rss_mb(), WORKER_RSS_LIMIT_MB)
                import os as _os
                _os._exit(0)
            log.info(f"--- DAEMON CYCLE #{cycle_count} COMPLETE. MEMORY TRIMMED ---")
        except KeyboardInterrupt:
            log.info("Daemon interrupted by user. Stopping cleanly...")
            break
        except Exception as exc:
            log.error(f"Daemon cycle #{cycle_count} encountered error: {exc}", exc_info=True)
            trim_memory()
            if _rss_mb() > WORKER_RSS_LIMIT_MB:
                log.warning('RSS watchdog: %.1f MB > %.0f MB limit - restarting worker cleanly', _rss_mb(), WORKER_RSS_LIMIT_MB)
                import os as _os
                _os._exit(0)
        
        # 60-second cadence between scan cycles (Quality Trade Mandate):
        # 1. Swing positions are managed on structural levels, not tick noise
        # 2. Slashes CPU/RAM churn on 512MB Render instances (fewer allocations/sec)
        # 3. Still keeps trailing stops and exits monitored well within tolerance
        time.sleep(60)
