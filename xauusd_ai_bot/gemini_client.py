import json
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from config import config
from logger import logger
from models import GeminiAnalysisResponse


SYSTEM_PROMPT = """You are a master ICT (Inner Circle Trader) and Smart Money Concepts (SMC) quantitative analyst specializing strictly in XAUUSD (Gold/USD).

CRITICAL LANGUAGE & SCENARIO REQUIREMENT:
- All 'reasoning', 'setup_type', 'market_structure', 'warnings', 'bullish_scenario', and 'bearish_scenario' MUST be written in clear, professional ARABIC (اللغة العربية الفصحى).
- You MUST provide both:
  1. 'bullish_scenario': Clear Arabic description of the Bullish ICT setup path & conditions.
  2. 'bullish_probability': Integer percentage probability for the Bullish scenario (e.g. 60).
  3. 'bearish_scenario': Clear Arabic description of the Bearish ICT setup path & conditions.
  4. 'bearish_probability': Integer percentage probability for the Bearish scenario (e.g. 40).
  (Note: bullish_probability + bearish_probability MUST equal 100).

YOUR TRADING FRAMEWORK (ICT / SMC ONLY):
1. MARKET STRUCTURE & SHIFT (MSS / CHOCH):
   - Bullish setup requires Market Structure Shift (MSS / CHOCH) or Break of Structure (BOS) to the upside.
   - Bearish setup requires Market Structure Shift (MSS / CHOCH) or Break of Structure (BOS) to the downside.
2. LIQUIDITY SWEEPS:
   - Identify if Buy-Side Liquidity (BSL) or Sell-Side Liquidity (SSL) was swept prior to displacement.
3. FAIR VALUE GAPS (FVG) & ORDER BLOCKS (OB):
   - BUY entries MUST target a Bullish Order Block (OB) or Bullish Fair Value Gap (FVG) discount retest.
   - SELL entries MUST target a Bearish Order Block (OB) or Bearish Fair Value Gap (FVG) premium retest.
4. PREMIUM vs DISCOUNT PRICING:
   - ONLY BUY when price is in DISCOUNT (below 50% Equilibrium).
   - ONLY SELL when price is in PREMIUM (above 50% Equilibrium).

RULES:
- Use ONLY the supplied market data. Never invent prices or candles.
- The application MUST NEVER execute trades automatically. Analysis only.
- If ICT/SMC conditions are NOT met (no clear FVG/OB retest, no MSS, or conflicting liquidity sweeps), return "NO_TRADE".
- For LONG: Stop Loss below Bullish OB/Invalidation level; Targets (TP1, TP2, TP3) at Buy-side Liquidity targets above.
- For SHORT: Stop Loss above Bearish OB/Invalidation level; Targets (TP1, TP2, TP3) at Sell-side Liquidity targets below.
- Write all reasoning bullet points in clear ARABIC (اللغة العربية الفصحى) focusing strictly on ICT/SMC concepts.
"""


class GeminiClient:
    """Interface to Google Gemini API using the official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or config.gemini_api_key
        self.model_name = model_name or config.gemini_model
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    def analyze_market_snapshot(self, market_context: Dict[str, Any]) -> Optional[GeminiAnalysisResponse]:
        """
        Sends formatted technical market context to Gemini API and parses the structured response.
        """
        if not self.client:
            logger.error("Gemini API key is not configured. Cannot perform AI analysis.")
            return None

        prompt = f"""Analyze the following real-time XAUUSD market snapshot and provide your structured technical trading analysis:

MARKET SNAPSHOT DATA:
{json.dumps(market_context, indent=2)}

INSTRUCTIONS:
Determine whether conditions justify a LONG, SHORT, or NO_TRADE setup based strictly on technical confluence.
Return your evaluation in the required JSON format.
"""

        # Model fallback candidate list
        candidate_models = [self.model_name, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for model in candidate_models:
            for attempt in range(1, 3):
                try:
                    logger.info(f"GEMINI REQUEST STARTED: Model={model} (attempt {attempt})")
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_schema=GeminiAnalysisResponse,
                            temperature=0.2,
                        )
                    )

                    raw_text = response.text
                    logger.info(f"GEMINI RESPONSE RECEIVED (Model={model})")
                    logger.debug(f"Raw Gemini Output: {raw_text}")

                    # Parse JSON using Pydantic model
                    analysis_data = json.loads(raw_text)
                    parsed_response = GeminiAnalysisResponse.model_validate(analysis_data)
                    return parsed_response

                except Exception as e:
                    logger.warning(f"Gemini model {model} attempt {attempt} failed: {e}")
                    import time
                    time.sleep(2.0 * attempt)

        logger.error("All Gemini API models failed after retries.")
        return None
