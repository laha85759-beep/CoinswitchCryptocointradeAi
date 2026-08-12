"""
1min.AI Integration Client Module
=================================
Provides AI sentiment analysis, multi-modal chart pattern recognition,
and market news summary using the 1min.AI API platform.
"""
import os
import logging
import requests
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


class OneMinAIClient:
    """Client wrapper for 1min.AI API services."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ONEMIN_AI_API_KEY", "5bbdd65d81492ca76dba5f864a7f0125e1bc0a2f6801c3a8134696d28327ffcd")
        self.base_url = "https://api.1min.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def analyze_sentiment(self, text_prompt: str) -> Dict[str, Any]:
        """Analyze market news or text prompt using 1min.AI LLM models."""
        if not self.api_key:
            return {"status": "skipped", "reason": "missing_api_key"}

        try:
            payload = {
                "prompt": text_prompt,
                "type": "text_analysis"
            }
            res = requests.post(f"{self.base_url}/v1/chat/completions", headers=self.headers, json=payload, timeout=10)
            if res.status_code == 200:
                return res.json()
            log.warning("1min.AI API returned status %s: %s", res.status_code, res.text[:200])
            return {"status": "error", "code": res.status_code, "response": res.text[:200]}
        except Exception as exc:
            log.error("1min.AI sentiment analysis failed: %s", exc)
            return {"status": "error", "reason": str(exc)}
