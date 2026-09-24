import json
import logging
from openai import OpenAI

log = logging.getLogger(__name__)

class NemotronAnalysisAgent:
    """
    Leverages Nvidia's Nemotron-3-Ultra-550B via the OpenAI client
    to analyze trade signals and ensure high-probability trade execution.
    """
    def __init__(self, api_key: str = "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"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model = "nvidia/nemotron-3-ultra-550b-a55b"

    def analyze_signal(self, signal: dict, current_price: float) -> dict:
        """
        Takes a raw trading signal and current market context.
        Returns a dict with 'approved' (bool) and 'reason' (str).
        """
        symbol = signal.get("symbol", "UNKNOWN")
        direction = signal.get("signal", "unknown")
        
        prompt = f"""
        You are an elite quantitative trading AI.
        Analyze this incoming trade signal:
        - Symbol: {symbol}
        - Direction: {direction}
        - Current Price: {current_price}
        - Original Confidence: {signal.get('confidence', 1.0)}

        Determine if this is a high-probability trade. Consider market mean-reversion, breakout sustainability, and general crypto volatility.
        Return ONLY valid JSON in this exact format, with no markdown formatting or backticks:
        {{
            "approved": true or false,
            "reason": "Brief explanation of your deep reasoning."
        }}
        """

        try:
            log.info("Sending signal to Nemotron for deep reasoning analysis: %s %s", symbol, direction)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                top_p=0.95,
                max_tokens=1024,
                # Not using extra_body reasoning_budget to ensure strict JSON output and no stream
                stream=False
            )
            
            content = completion.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            content = content.strip()
            result = json.loads(content)
            
            return {
                "approved": bool(result.get("approved", False)),
                "reason": result.get("reason", "Nemotron parsed but missing reason")
            }
            
        except Exception as e:
            log.error("Nemotron analysis failed: %s", e)
            # Default to approve if LLM fails, so we don't break the pipeline, but log the error
            return {
                "approved": True,
                "reason": f"LLM error fallback (approved): {str(e)}"
            }
