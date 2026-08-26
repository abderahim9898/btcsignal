import requests
from pathlib import Path
from typing import Optional
from config import config
from logger import logger
from models import FullAnalysisResult
from utils import parse_iso_datetime, format_morocco_time


class TelegramNotifier:
    """Handles Telegram bot message formatting in Arabic and sending text/photos via Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or config.telegram_bot_token
        self.chat_id = chat_id or config.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def send_analysis_notification(self, analysis: FullAnalysisResult, chart_path: Optional[str] = None, only_signals: bool = False) -> bool:
        """Formats and dispatches Arabic Telegram notification for analysis result (with photo and full text)."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram token or chat_id not configured. Skipping notification.")
            return False

        # Skip notification if only_signals is active and signal is NO_TRADE
        if (only_signals or config.only_send_trade_signals) and analysis.signal == "NO_TRADE":
            logger.info("SIGNAL IS NO_TRADE and ONLY_SEND_TRADE_SIGNALS is enabled. Skipping Telegram dispatch.")
            return True

        full_message = self.format_arabic_message(analysis)

        # 1. Send Chart Photo if available
        if chart_path and Path(chart_path).exists():
            sig_emoji = "🟢" if analysis.signal == "LONG" else "🔴" if analysis.signal == "SHORT" else "⚪"
            photo_caption = (
                f"📊 <b>رسم بياني لـ XAUUSD ({config.timeframe}) - ICT/SMC Analysis</b>\n"
                f"📌 <b>الإشارة:</b> {sig_emoji} {analysis.signal} ({analysis.confidence}%)\n"
                f"💰 <b>السعر:</b> {analysis.current_price:.2f}$ | ⏰ <b>الوقت:</b> {analysis.candle_time}"
            )
            self._send_photo_message(photo_caption, chart_path)

        # 2. Send Full Untruncated Arabic Report
        return self._send_text_message(full_message)

    def _send_photo_message(self, text: str, image_path: str) -> bool:
        """Sends photo with Arabic caption to Telegram API."""
        # Truncate caption if longer than Telegram's 1024 character limit for sendPhoto
        caption = text
        if len(caption) > 1000:
            caption = caption[:950] + "\n...\n━━━━━━━━━━━━━━━━━━━━\n⚠️ <i>هذا تحليل فني وإشعار فقط.</i>"

        url = f"{self.base_url}/sendPhoto"
        try:
            logger.info("TELEGRAM REQUEST STARTED (sendPhoto)")
            with open(image_path, "rb") as photo_file:
                payload = {
                    "chat_id": self.chat_id,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                files = {"photo": photo_file}
                response = requests.post(url, data=payload, files=files, timeout=15)
                response.raise_for_status()
                logger.info("TELEGRAM SENT: Photo & Arabic Notification dispatched successfully.")
                return True
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            return False

    def _send_text_message(self, text: str) -> bool:
        """Sends text message to Telegram API."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            logger.info("TELEGRAM REQUEST STARTED (sendMessage)")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("TELEGRAM SENT: Arabic Text Notification dispatched successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram text message: {e}")
            return False

    def format_arabic_message(self, a: FullAnalysisResult) -> str:
        """Formats analysis result into clean Arabic HTML formatted Telegram message."""
        # Convert UTC candle_time to Morocco Local Time
        try:
            dt = parse_iso_datetime(a.candle_time)
            time_str = format_morocco_time(dt)
        except Exception:
            time_str = f"{a.candle_time} بتوقيت المغرب"

        if a.signal == "NO_TRADE":
            lines = [
                "========================================",
                "🟡 <b>تحليل الذهب الذكي (XAUUSD AI ANALYSIS)</b>",
                "========================================",
                "",
                f"⏰ <b>الوقت:</b> {time_str}",
                f"📊 <b>الإطار الزمني:</b> {a.timeframe}",
                f"💰 <b>السعر الحالي:</b> {a.current_price:.2f}$",
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                "📌 <b>الإشارة:</b> ⚪ <b>عدم الدخول (NO TRADE)</b>",
                f"🎯 <b>نسبة الثقة الفنية:</b> {a.confidence}%",
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                f"📈 <b>هيكل السوق:</b> {a.market_structure or 'تضارب في الإشارات'}",
                f"🌪 <b>التقلبات:</b> {a.volatility}",
                "",
                "🟢 <b>مناطق الدعم:</b>",
                a.support_zones or "لا توجد",
                "",
                "🔴 <b>مناطق المقاومة:</b>",
                a.resistance_zones or "لا توجد",
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                "🧠 <b>الأسباب الفنية (ICT / SMC):</b>",
            ]
            for r in a.reasoning.split("\n"):
                if r.strip():
                    lines.append(f"• {r.strip()}")

            if a.warnings:
                lines.append("")
                lines.append("⚠️ <b>تنبيهات فنية:</b>")
                for w in a.warnings.split("\n"):
                    if w.strip():
                        lines.append(f"• {w.strip()}")

            if a.bullish_scenario or a.bearish_scenario:
                lines.extend([
                    "",
                    "━━━━━━━━━━━━━━━━━━━━",
                    "",
                    "🔮 <b>السيناريوهات المتوقعة والاحتمالات (ICT Scenarios):</b>"
                ])
                if a.bullish_scenario:
                    lines.append(f"🟢 <b>السيناريو الصاعد ({a.bullish_probability}%):</b>\n• {a.bullish_scenario}")
                if a.bearish_scenario:
                    lines.append(f"🔴 <b>السيناريو الهابط ({a.bearish_probability}%):</b>\n• {a.bearish_scenario}")

            lines.extend([
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "⚠️ <i>هذا تحليل فني وإشعار فقط. لا يوجد أي تنفيذ تلقائي لصفقات التداول.</i>",
                "========================================"
            ])
            return "\n".join(lines)

        # LONG or SHORT setup message in Arabic
        signal_emoji = "🟢 شراء (LONG)" if a.signal == "LONG" else "🔴 بيع (SHORT)"

        # Format Risk/Reward
        rr_tp1_str = f"1:{a.risk_reward_tp1:.1f}" if a.risk_reward_tp1 else "N/A"
        rr_tp2_str = f"1:{a.risk_reward_tp2:.1f}" if a.risk_reward_tp2 else "N/A"
        rr_tp3_str = f"1:{a.risk_reward_tp3:.1f}" if a.risk_reward_tp3 else "N/A"

        lines = [
            "========================================",
            "🟡 <b>تحليل الذهب الذكي (XAUUSD AI ANALYSIS)</b>",
            "========================================",
            "",
            f"⏰ <b>الوقت:</b> {time_str}",
            f"📊 <b>الإطار الزمني:</b> {a.timeframe}",
            f"💰 <b>السعر الحالي:</b> {a.current_price:.2f}$",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            f"📌 <b>الإشارة:</b> <b>{signal_emoji}</b>",
            f"🎯 <b>نسبة الثقة الفنية:</b> {a.confidence}%",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            f"🟢 <b>سعر الدخول (ENTRY):</b> {a.entry:.2f}$" if a.entry else "🟢 <b>سعر الدخول:</b> غير محدد",
            f"🛑 <b>وقف الخسارة (STOP LOSS):</b> {a.stop_loss:.2f}$" if a.stop_loss else "🛑 <b>وقف الخسارة:</b> غير محدد",
            f"🎯 <b>الهدف الأول (TP1):</b> {a.take_profit_1:.2f}$" if a.take_profit_1 else "🎯 <b>الهدف الأول:</b> غير محدد",
        ]

        if a.take_profit_2:
            lines.append(f"🎯 <b>الهدف الثاني (TP2):</b> {a.take_profit_2:.2f}$")
        if a.take_profit_3:
            lines.append(f"🎯 <b>الهدف الثالث (TP3):</b> {a.take_profit_3:.2f}$")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "📊 <b>نسبة المخاطرة إلى المكافأة (RISK / REWARD):</b>",
            "",
            f"الهدف 1: {rr_tp1_str}",
        ])
        if a.take_profit_2:
            lines.append(f"الهدف 2: {rr_tp2_str}")
        if a.take_profit_3:
            lines.append(f"الهدف 3: {rr_tp3_str}")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            f"📈 <b>هيكل السوق (ICT/SMC):</b> {a.market_structure}",
            f"🔥 <b>النموذج الفني:</b> {a.setup_type}",
            f"🌪 <b>التقلبات:</b> {a.volatility}",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "🟢 <b>مناطق الدعم:</b>",
            a.support_zones or "لا توجد",
            "",
            "🔴 <b>مناطق المقاومة:</b>",
            a.resistance_zones or "لا توجد",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "🧠 <b>الأسباب الفنية للتحليل:</b>",
        ])

        for r in a.reasoning.split("\n"):
            if r.strip():
                lines.append(f"• {r.strip()}")

        if a.invalidation_level:
            lines.extend([
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                f"⚠️ <b>مستوى إلغاء الصفقة:</b> {a.invalidation_level:.2f}$"
            ])

        if a.bullish_scenario or a.bearish_scenario:
            lines.extend([
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                "🔮 <b>السيناريوهات المتوقعة والاحتمالات (ICT Scenarios):</b>"
            ])
            if a.bullish_scenario:
                lines.append(f"🟢 <b>السيناريو الصاعد ({a.bullish_probability}%):</b>\n• {a.bullish_scenario}")
            if a.bearish_scenario:
                lines.append(f"🔴 <b>السيناريو الهابط ({a.bearish_probability}%):</b>\n• {a.bearish_scenario}")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "⚠️ <i>هذا تحليل فني وإشعار فقط. لا يوجد أي تنفيذ تلقائي لصفقات التداول.</i>",
            "========================================"
        ])

        return "\n".join(lines)
