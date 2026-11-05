"""
Ahrefs AI Brand & Site Explorer Tracker
Tracks AI mentions and search visibility across ChatGPT, Google AI Overviews, Gemini, Perplexity, Copilot, Grok
Target: trade.thesmartmag.com
"""
import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger("AhrefsTracker")

class AhrefsTracker:
    def __init__(self, api_key: str = None, target: str = "trade.thesmartmag.com/"):
        self.api_key = api_key or os.environ.get("AHREFS_API_KEY", "")
        self.target = target
        self.base_url = "https://api.ahrefs.com/v3/site-explorer"

    def get_ai_responses_count(self, select: str = "all_platforms,chatgpt,google_ai_overviews,google_ai_overviews_keywords,google_ai_mode,gemini,perplexity,copilot,grok"):
        if not self.api_key:
            return {"error": "AHREFS_API_KEY not configured", "success": False}

        url = f"{self.base_url}/ai-responses-count"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "target": self.target,
            "select": select
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            else:
                return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            logger.error(f"Error fetching Ahrefs AI data: {e}")
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    load_dotenv()
    tracker = AhrefsTracker()
    result = tracker.get_ai_responses_count()
    print("Ahrefs tracking result:", result)
