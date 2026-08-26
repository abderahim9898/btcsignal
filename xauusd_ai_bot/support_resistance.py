from typing import List, Dict, Tuple, Any
import numpy as np
import pandas as pd
from market_structure import find_swing_points


def find_support_resistance_zones(
    df: pd.DataFrame,
    current_price: float,
    lookback: int = 100,
    tolerance_pct: float = 0.0015
) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    """
    Identifies key support and resistance zones based on swing point clustering and price extrema.
    Returns (support_zones, resistance_zones).
    """
    if len(df) < 20:
        return [], []

    subset = df.iloc[-lookback:].reset_index(drop=True)
    swing_highs, swing_lows = find_swing_points(subset, left=2, right=2)

    all_pivots = [sh["price"] for sh in swing_highs] + [sl["price"] for sl in swing_lows]
    if not all_pivots:
        return [], []

    # Cluster pivots that are within tolerance
    clusters: List[List[float]] = []
    for price in sorted(all_pivots):
        matched = False
        for c in clusters:
            avg_c = np.mean(c)
            if abs(price - avg_c) / avg_c <= tolerance_pct:
                c.append(price)
                matched = True
                break
        if not matched:
            clusters.append([price])

    # Convert clusters into zones
    support_zones = []
    resistance_zones = []

    for c in clusters:
        zone_min = round(float(np.min(c)), 2)
        zone_max = round(float(np.max(c)), 2)
        # Pad zone if it's a single price point
        if zone_min == zone_max:
            zone_min = round(zone_min - 0.5, 2)
            zone_max = round(zone_max + 0.5, 2)

        zone_avg = (zone_min + zone_max) / 2.0

        zone_dict = {"low": zone_min, "high": zone_max, "touch_count": len(c)}

        if zone_avg < current_price:
            support_zones.append(zone_dict)
        else:
            resistance_zones.append(zone_dict)

    # Sort support descending (closest to price first) and resistance ascending (closest to price first)
    support_zones = sorted(support_zones, key=lambda x: x["high"], reverse=True)[:3]
    resistance_zones = sorted(resistance_zones, key=lambda x: x["low"])[:3]

    return support_zones, resistance_zones


def format_sr_zones_str(zones: List[Dict[str, float]]) -> List[str]:
    """Formats zone dictionaries into human-readable string representations like '3348.50 - 3352.00'."""
    return [f"{z['low']} - {z['high']}" for z in zones]
