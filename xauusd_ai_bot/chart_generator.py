import os
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from indicators import calculate_ema
from models import FullAnalysisResult
from support_resistance import find_support_resistance_zones
from smc_ict import detect_fair_value_gaps, detect_order_blocks, detect_liquidity_sweeps, calculate_premium_discount
from market_structure import find_swing_points
from logger import logger


def generate_candlestick_chart(
    df: pd.DataFrame,
    analysis: Optional[FullAnalysisResult] = None,
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Generates a clean, modern, dark-themed 200-candle PNG chart with minimal,
    eye-pleasing ICT overlays (Support/Resistance, FVGs, BSL/SSL Liquidity).
    Saves image to output_path and returns the filepath.
    """
    if df is None or len(df) < 10:
        return None

    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    if not output_path:
        output_path = str(log_dir / "chart_latest.png")

    try:
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 6), dpi=150)

        # Set custom elegant dark background color
        fig.patch.set_facecolor('#111622')
        ax.set_facecolor('#111622')

        # Subset last 200 candles for clean visualization
        subset = df.iloc[-200:].copy().reset_index(drop=True)
        subset["dt"] = pd.to_datetime(subset["timestamp"])

        # Compute EMAs
        subset["ema20"] = calculate_ema(subset["close"], 20)
        subset["ema50"] = calculate_ema(subset["close"], 50)
        subset["ema200"] = calculate_ema(subset["close"], 200)

        # Plot Candlesticks (Clean Teal & Coral Red)
        for i, row in subset.iterrows():
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            # High-Low Wick
            ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.7, alpha=0.85)
            # Open-Close Body
            body_bottom = min(row['open'], row['close'])
            body_top = max(row['open'], row['close'])
            body_height = max(0.05, body_top - body_bottom)
            rect = plt.Rectangle((i - 0.4, body_bottom), 0.8, body_height, color=color, alpha=0.85)
            ax.add_patch(rect)

        # Plot EMAs (Subtle, thin lines)
        ax.plot(subset.index, subset["ema20"], color='#4dd0e1', linewidth=0.9, alpha=0.6, label='EMA 20')
        ax.plot(subset.index, subset["ema50"], color='#ffb74d', linewidth=0.9, alpha=0.6, label='EMA 50')
        ax.plot(subset.index, subset["ema200"], color='#f06292', linewidth=0.9, alpha=0.4, label='EMA 200')

        # 1. Plot Support and Resistance Zones (Soft low-opacity tint)
        last_price = subset.iloc[-1]["close"]
        s_zones, r_zones = find_support_resistance_zones(df, current_price=last_price)

        for s in s_zones[:2]:  # Support zones (soft teal tint)
            ax.axhspan(s["low"], s["high"], color='#26a69a', alpha=0.09, linestyle='-', linewidth=0.5)
            ax.text(2, s["high"], f" Support ({s['low']:.1f}-{s['high']:.1f})", color='#4db6ac', fontsize=7, alpha=0.8, va='bottom')

        for r in r_zones[:2]:  # Resistance zones (soft coral tint)
            ax.axhspan(r["low"], r["high"], color='#ef5350', alpha=0.09, linestyle='-', linewidth=0.5)
            ax.text(2, r["low"], f" Resistance ({r['low']:.1f}-{r['high']:.1f})", color='#e57373', fontsize=7, alpha=0.8, va='top')

        # 2. Plot Fair Value Gaps (FVG) ONLY in DISCOUNT Zone (Below Equilibrium 50%)
        prem_disc = calculate_premium_discount(df)
        eq_level = prem_disc.get("equilibrium", 0.0)

        # Plot 50% Equilibrium Line
        if eq_level > 0:
            ax.axhline(y=eq_level, color='#78909c', linestyle=':', linewidth=0.8, alpha=0.5)
            ax.text(170, eq_level, f" 50% EQ ({eq_level:.1f})", color='#78909c', fontsize=6.5, alpha=0.7, va='bottom')

        fvgs = detect_fair_value_gaps(df, min_gap_size=0.3)
        # Strict ICT Rule: Filter only FVGs located in DISCOUNT zone (midpoint <= eq_level)
        discount_fvgs = [fvg for fvg in fvgs if (fvg["bottom"] + fvg["top"]) / 2.0 <= eq_level or eq_level == 0.0]

        for fvg in discount_fvgs[-3:]:  # Latest 3 Discount FVGs
            fvg_color = '#ffb74d' if fvg["type"] == "BULLISH_FVG" else '#ba68c8'
            fvg_label = f"FVG ({fvg['bottom']:.1f}-{fvg['top']:.1f})"

            # Find starting candle index in subset
            match_mask = subset["timestamp"] == fvg["candle_time"]
            start_x = subset[match_mask].index[0] if match_mask.any() else 0
            end_x = len(subset) - 1
            width = max(5, end_x - start_x + 1)
            height = fvg["top"] - fvg["bottom"]

            # Draw FVG rectangle box starting at formation candle
            fvg_rect = plt.Rectangle(
                (start_x, fvg["bottom"]), width, height,
                facecolor=fvg_color, alpha=0.12, edgecolor=fvg_color, linestyle=':', linewidth=0.7
            )
            ax.add_patch(fvg_rect)
            ax.text(start_x + 2, (fvg["bottom"] + fvg["top"]) / 2, fvg_label, color=fvg_color, fontsize=6.5, alpha=0.9, va='center')

        # 3. Plot Liquidity Zones (BSL / SSL) (Thin dashed lines)
        swing_highs, swing_lows = find_swing_points(subset, left=3, right=3)
        if swing_highs:
            latest_bsl = swing_highs[-1]["price"]
            ax.axhline(y=latest_bsl, color='#ffe082', linestyle='--', linewidth=0.7, alpha=0.65)
            ax.text(150, latest_bsl, f" BSL ({latest_bsl:.1f})", color='#ffe082', fontsize=6.5, alpha=0.8, va='bottom')

        if swing_lows:
            latest_ssl = swing_lows[-1]["price"]
            ax.axhline(y=latest_ssl, color='#80deea', linestyle='--', linewidth=0.7, alpha=0.65)
            ax.text(150, latest_ssl, f" SSL ({latest_ssl:.1f})", color='#80deea', fontsize=6.5, alpha=0.8, va='top')

        # 4. Plot Swept Liquidity (السيولة المسحوبة)
        sweeps = detect_liquidity_sweeps(df, lookback=80)
        for sweep in sweeps[-1:]:  # Plot latest sweep
            marker = 'v' if sweep["type"] == "BUY_SIDE_LIQUIDITY_SWEEP" else '^'
            marker_color = '#ef5350' if sweep["type"] == "BUY_SIDE_LIQUIDITY_SWEEP" else '#26a69a'
            sw_label = f"Swept BSL ({sweep['swept_level']:.1f})" if sweep["type"] == "BUY_SIDE_LIQUIDITY_SWEEP" else f"Swept SSL ({sweep['swept_level']:.1f})"
            ax.axhline(y=sweep["swept_level"], color=marker_color, linestyle=':', alpha=0.5, linewidth=0.7)
            ax.plot(len(subset) - 5, sweep["swept_level"], marker=marker, color=marker_color, markersize=7, alpha=0.9)
            ax.text(len(subset) - 30, sweep["swept_level"], f" {sw_label}", color=marker_color, fontsize=6.5, alpha=0.85, va='center')

        # 5. Plot Entry, SL, TP Lines if signal active
        if analysis and analysis.signal in ["LONG", "SHORT"]:
            if analysis.entry:
                ax.axhline(y=analysis.entry, color='#00e676', linestyle='--', linewidth=1.2, label=f'Entry: {analysis.entry}')
            if analysis.stop_loss:
                ax.axhline(y=analysis.stop_loss, color='#ff1744', linestyle='--', linewidth=1.2, label=f'SL: {analysis.stop_loss}')
            if analysis.take_profit_1:
                ax.axhline(y=analysis.take_profit_1, color='#00b0ff', linestyle=':', linewidth=1.2, label=f'TP1: {analysis.take_profit_1}')

        # Styling & Layout
        sig_str = f"{analysis.signal} ({analysis.confidence}%)" if analysis else "SNAPSHOT"
        c_time = analysis.candle_time if analysis else str(subset.iloc[-1]["timestamp"])
        sym_str = config.symbol.upper()
        ax.set_title(f"{sym_str} ({config.timeframe}) ICT/SMC Analysis - {sig_str} | {c_time}", fontsize=10.5, fontweight='bold', pad=10, color='#eceff1')
        ax.set_ylabel("Price (USD)", fontsize=8.5, color='#b0bec5')
        ax.grid(True, linestyle=':', alpha=0.15)
        ax.legend(loc='upper left', fontsize=7.5, framealpha=0.4)

        # X-axis formatting
        tick_locs = np.linspace(0, len(subset) - 1, min(12, len(subset)), dtype=int)
        tick_labels = [subset.iloc[t]["dt"].strftime("%H:%M") for t in tick_locs]
        ax.set_xticks(tick_locs)
        ax.set_xticklabels(tick_labels, fontsize=7.5, color='#b0bec5')
        ax.tick_params(colors='#b0bec5')

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)

        logger.info(f"CHART GENERATED: Clean minimalist chart saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate chart image: {e}")
        return None
