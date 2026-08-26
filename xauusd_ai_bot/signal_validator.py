from typing import Optional, Tuple
from config import config
from logger import logger
from models import GeminiAnalysisResponse, FullAnalysisResult


class SignalValidator:
    """Validates AI trading signals, price relationships, and computes Risk/Reward independently."""

    def __init__(self, min_confidence: int = config.min_confidence):
        self.min_confidence = min_confidence

    def validate_and_enrich(self, raw_resp: GeminiAnalysisResponse, raw_json_str: str = "") -> FullAnalysisResult:
        """
        Validates Gemini signal output, checks price hierarchy, computes Python Risk/Reward,
        and returns a FullAnalysisResult.
        """
        signal = raw_resp.signal
        confidence = raw_resp.confidence
        warnings = list(raw_resp.warnings or [])
        reasoning = list(raw_resp.reasoning or [])

        entry = raw_resp.entry
        sl = raw_resp.stop_loss
        tp1 = raw_resp.take_profit_1
        tp2 = raw_resp.take_profit_2
        tp3 = raw_resp.take_profit_3

        risk: Optional[float] = None
        reward_tp1: Optional[float] = None
        reward_tp2: Optional[float] = None
        reward_tp3: Optional[float] = None

        rr_tp1: Optional[float] = None
        rr_tp2: Optional[float] = None
        rr_tp3: Optional[float] = None

        # 1. Check Confidence Threshold
        if confidence < self.min_confidence and signal != "NO_TRADE":
            msg = f"Confidence ({confidence}%) below threshold ({self.min_confidence}%). Overriding signal to NO_TRADE."
            logger.info(f"SIGNAL OVERRIDE: {msg}")
            warnings.append(msg)
            signal = "NO_TRADE"

        # 2. Check LONG price relationships
        if signal == "LONG":
            if not (entry and sl and tp1):
                warnings.append("LONG signal missing entry, stop_loss, or take_profit_1.")
                signal = "NO_TRADE"
            elif sl >= entry:
                warnings.append(f"Invalid LONG SL: Stop Loss ({sl}) must be lower than Entry ({entry}).")
                signal = "NO_TRADE"
            elif tp1 <= entry:
                warnings.append(f"Invalid LONG TP1: Take Profit 1 ({tp1}) must be higher than Entry ({entry}).")
                signal = "NO_TRADE"
            elif tp2 and tp2 <= tp1:
                warnings.append(f"Invalid LONG TP2: TP2 ({tp2}) must be higher than TP1 ({tp1}).")
                signal = "NO_TRADE"
            elif tp3 and tp2 and tp3 <= tp2:
                warnings.append(f"Invalid LONG TP3: TP3 ({tp3}) must be higher than TP2 ({tp2}).")
                signal = "NO_TRADE"
            else:
                # Python Risk/Reward Calculation
                risk = round(entry - sl, 2)
                reward_tp1 = round(tp1 - entry, 2)
                reward_tp2 = round(tp2 - entry, 2) if tp2 else None
                reward_tp3 = round(tp3 - entry, 2) if tp3 else None

                if risk > 0:
                    rr_tp1 = round(reward_tp1 / risk, 2)
                    rr_tp2 = round(reward_tp2 / risk, 2) if reward_tp2 else None
                    rr_tp3 = round(reward_tp3 / risk, 2) if reward_tp3 else None
                else:
                    warnings.append("Calculated risk is zero or negative.")
                    signal = "NO_TRADE"

        # 3. Check SHORT price relationships
        elif signal == "SHORT":
            if not (entry and sl and tp1):
                warnings.append("SHORT signal missing entry, stop_loss, or take_profit_1.")
                signal = "NO_TRADE"
            elif sl <= entry:
                warnings.append(f"Invalid SHORT SL: Stop Loss ({sl}) must be higher than Entry ({entry}).")
                signal = "NO_TRADE"
            elif tp1 >= entry:
                warnings.append(f"Invalid SHORT TP1: Take Profit 1 ({tp1}) must be lower than Entry ({entry}).")
                signal = "NO_TRADE"
            elif tp2 and tp2 >= tp1:
                warnings.append(f"Invalid SHORT TP2: TP2 ({tp2}) must be lower than TP1 ({tp1}).")
                signal = "NO_TRADE"
            elif tp3 and tp2 and tp3 >= tp2:
                warnings.append(f"Invalid SHORT TP3: TP3 ({tp3}) must be lower than TP2 ({tp2}).")
                signal = "NO_TRADE"
            else:
                # Python Risk/Reward Calculation
                risk = round(sl - entry, 2)
                reward_tp1 = round(entry - tp1, 2)
                reward_tp2 = round(entry - tp2, 2) if tp2 else None
                reward_tp3 = round(entry - tp3, 2) if tp3 else None

                if risk > 0:
                    rr_tp1 = round(reward_tp1 / risk, 2)
                    rr_tp2 = round(reward_tp2 / risk, 2) if reward_tp2 else None
                    rr_tp3 = round(reward_tp3 / risk, 2) if reward_tp3 else None
                else:
                    warnings.append("Calculated risk is zero or negative.")
                    signal = "NO_TRADE"

        # 4. Clean up levels if NO_TRADE
        if signal == "NO_TRADE":
            entry = None
            sl = None
            tp1 = None
            tp2 = None
            tp3 = None
            risk = None
            reward_tp1 = None
            reward_tp2 = None
            reward_tp3 = None
            rr_tp1 = None
            rr_tp2 = None
            rr_tp3 = None

        logger.info(f"SIGNAL VALIDATED: Final Signal={signal}, Confidence={confidence}%, RR_TP1={rr_tp1}")

        result = FullAnalysisResult(
            symbol=raw_resp.symbol,
            timeframe=raw_resp.timeframe,
            candle_time=raw_resp.candle_time,
            analysis_time=raw_resp.analysis_time,
            current_price=raw_resp.current_price or 0.0,
            signal=signal,
            confidence=confidence,
            entry=entry,
            entry_zone_low=raw_resp.entry_zone_low if signal != "NO_TRADE" else None,
            entry_zone_high=raw_resp.entry_zone_high if signal != "NO_TRADE" else None,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk=risk,
            reward_tp1=reward_tp1,
            reward_tp2=reward_tp2,
            reward_tp3=reward_tp3,
            risk_reward_tp1=rr_tp1,
            risk_reward_tp2=rr_tp2,
            risk_reward_tp3=rr_tp3,
            trend=raw_resp.trend,
            trend_strength=raw_resp.trend_strength,
            momentum=raw_resp.momentum,
            volatility=raw_resp.volatility,
            setup_type=raw_resp.setup_type,
            support_zones="; ".join(raw_resp.support_zones),
            resistance_zones="; ".join(raw_resp.resistance_zones),
            invalidation_level=raw_resp.invalidation_level if signal != "NO_TRADE" else None,
            bullish_scenario=raw_resp.bullish_scenario,
            bullish_probability=raw_resp.bullish_probability,
            bearish_scenario=raw_resp.bearish_scenario,
            bearish_probability=raw_resp.bearish_probability,
            market_structure=raw_resp.market_structure,
            reasoning="\n".join(reasoning),
            warnings="\n".join(warnings),
            raw_gemini_response=raw_json_str,
            gemini_model=config.gemini_model
        )

        return result
