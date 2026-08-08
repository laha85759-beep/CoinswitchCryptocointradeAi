import logging
import requests

log = logging.getLogger(__name__)

class AISentimentAgent:
    """
    AI Sentiment News Filter.
    Fetches the latest Crypto Fear & Greed Index and recent macro news sentiment.
    Returns a normalized score from -100 (Extreme Fear) to +100 (Extreme Greed).
    """
    def __init__(self):
        self.api_url = "https://api.alternative.me/fng/?limit=1"

    def get_market_sentiment(self) -> dict:
        """
        Returns a dict:
        {
            "score": int (-100 to 100),
            "label": str,
            "can_long": bool,
            "can_short": bool
        }
        """
        try:
            resp = requests.get(self.api_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    # Alternative.me returns 0 (Extreme Fear) to 100 (Extreme Greed).
                    # We normalize this to -100 to +100.
                    raw_val = int(data[0].get("value", 50))
                    normalized_score = (raw_val - 50) * 2
                    label = data[0].get("value_classification", "Neutral")
                    
                    # Logic Rules:
                    # Extreme Fear (< -50) -> Don't Long
                    # Extreme Greed (> +50) -> Don't Short
                    can_long = normalized_score >= -50
                    can_short = normalized_score <= 50

                    return {
                        "score": normalized_score,
                        "label": label,
                        "can_long": can_long,
                        "can_short": can_short,
                        "raw_fng": raw_val
                    }
        except Exception as exc:
            log.warning("Failed to fetch sentiment from Alternative.me: %s", exc)
        
        # Fallback to neutral if API fails
        return {
            "score": 0,
            "label": "Neutral",
            "can_long": True,
            "can_short": True,
            "raw_fng": 50
        }
