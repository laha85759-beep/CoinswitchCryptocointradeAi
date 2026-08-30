import logging
import json
import requests

log = logging.getLogger("NVIDIA_NEMOTRON_AGENT")


class NVIDIANemotronAgent:
    """NVIDIA Nemotron 550B AI reasoning agent for crypto quant trading."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.api_key = cfg.get("nvidia_api_key")
        self.base_url = cfg.get("nvidia_base_url", "https://integrate.api.nvidia.com/v1")
        self.model_name = cfg.get("nvidia_model", "nvidia/nemotron-3-ultra-550b-a55b")
        log.info("NVIDIANemotronAgent: Configured for NVIDIA NIM (%s) ✅", self.model_name)

    def verify_trade_signal(self, symbol: str, signal_type: str, candidate_data: dict) -> dict:
        """
        Uses NVIDIA Nemotron 550B reasoning model to evaluate a candidate trade setup.
        Returns: {"approved": bool, "confidence": float, "reasoning": str}
        """
        if not self.api_key:
            log.warning("NVIDIANemotronAgent: API Key missing, returning default pass.")
            return {"approved": True, "confidence": candidate_data.get("confidence", 0.75), "reasoning": "Fallback: Key missing"}

        prompt = (
            f"You are an elite quantitative crypto trader. Analyze this 5m/1h market signal:\n"
            f"• Symbol: {symbol}\n"
            f"• Proposed Signal: {signal_type.upper()}\n"
            f"• 5m Change: {candidate_data.get('change_5m', 0.0):+.2f}%\n"
            f"• 1h Change: {candidate_data.get('change_1h', 0.0):+.2f}%\n"
            f"• Volume Z-Score: {candidate_data.get('volume_zscore', 1.0):.2f}\n"
            f"• Order Book Imbalance: {candidate_data.get('orderbook_imbalance', 0.5):.2f}\n\n"
            f"Evaluate if this setup is a high-conviction trade or a false breakout trap.\n"
            f"Reply ONLY in JSON format: {{\"approved\": true, \"confidence\": 0.85, \"reasoning\": \"short_explanation\"}}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a professional quantitative financial reasoning AI."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 500
        }

        try:
            log.info("Querying NVIDIA Nemotron 550B for %s (%s)...", symbol, signal_type)
            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                choice = data["choices"][0]["message"]
                response_text = choice.get("content") or ""
                reasoning_content = choice.get("reasoning_content")

                if reasoning_content:
                    log.info("NVIDIA Nemotron 550B Deep Thinking: %s", reasoning_content[:200])

                # Parse JSON response
                cleaned = response_text.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()

                parsed = json.loads(cleaned)
                log.info("NVIDIA Nemotron 550B Decision for %s: Approved=%s | Confidence=%s", 
                         symbol, parsed.get("approved"), parsed.get("confidence"))
                return parsed

            else:
                log.warning("NVIDIA NIM API HTTP %s: %s", resp.status_code, resp.text[:200])
                return {"approved": True, "confidence": candidate_data.get("confidence", 0.75), "reasoning": f"HTTP {resp.status_code}"}

        except Exception as exc:
            log.warning("NVIDIA Nemotron 550B query warning: %s. Using candidate baseline.", exc)
            return {
                "approved": True,
                "confidence": candidate_data.get("confidence", 0.75),
                "reasoning": f"Fallback error: {exc}"
            }
