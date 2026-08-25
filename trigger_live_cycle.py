import sys
import logging

sys.path.insert(0, ".")
import main

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("TRIGGER_CYCLE")

print("==================================================")
print("     STARTING LIVE DUAL-EXCHANGE TRADING CYCLE     ")
print("==================================================")

try:
    main.run()
    print("\n[SUCCESS] Bot cycle executed successfully!")
except Exception as e:
    import traceback
    print(f"\n[ERROR] Bot cycle error: {e}")
    traceback.print_exc()

print("==================================================")
