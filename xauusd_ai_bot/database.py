import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from config import config
from logger import logger
from models import FullAnalysisResult
from utils import get_current_utc_time


class DatabaseManager:
    """Handles SQLite connection, schema creation, deduplication checks, and persistence."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or config.db_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a sqlite3 connection with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates the analyses table with UNIQUE constraint if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analyses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        candle_time TEXT NOT NULL,
                        analysis_time TEXT NOT NULL,
                        current_price REAL,
                        signal TEXT NOT NULL,
                        confidence INTEGER,
                        entry REAL,
                        entry_zone_low REAL,
                        entry_zone_high REAL,
                        stop_loss REAL,
                        take_profit_1 REAL,
                        take_profit_2 REAL,
                        take_profit_3 REAL,
                        risk_reward_tp1 REAL,
                        risk_reward_tp2 REAL,
                        risk_reward_tp3 REAL,
                        trend TEXT,
                        trend_strength INTEGER,
                        momentum TEXT,
                        volatility TEXT,
                        setup_type TEXT,
                        support_zones TEXT,
                        resistance_zones TEXT,
                        invalidation_level REAL,
                        bullish_scenario TEXT,
                        bullish_probability INTEGER,
                        bearish_scenario TEXT,
                        bearish_probability INTEGER,
                        market_structure TEXT,
                        reasoning TEXT,
                        warnings TEXT,
                        raw_gemini_response TEXT,
                        gemini_model TEXT,
                        created_at TEXT NOT NULL,
                        UNIQUE(symbol, timeframe, candle_time)
                    )
                """)
                # Migrations for existing DB if needed
                for col_def in [
                    ("bullish_scenario", "TEXT"),
                    ("bullish_probability", "INTEGER"),
                    ("bearish_scenario", "TEXT"),
                    ("bearish_probability", "INTEGER")
                ]:
                    try:
                        cursor.execute(f"ALTER TABLE analyses ADD COLUMN {col_def[0]} {col_def[1]}")
                    except Exception:
                        pass
                conn.commit()
            logger.info(f"DATABASE INITIALIZED: Table 'analyses' ready at {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def is_candle_analyzed(self, symbol: str, timeframe: str, candle_time: str) -> bool:
        """Checks if a record with the same symbol, timeframe, and candle_time already exists."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM analyses WHERE symbol = ? AND timeframe = ? AND candle_time = ?",
                    (symbol, timeframe, candle_time)
                )
                row = cursor.fetchone()
                return row is not None
        except Exception as e:
            logger.error(f"Error checking candle deduplication: {e}")
            return False

    def save_analysis(self, analysis: FullAnalysisResult) -> bool:
        """Saves a validated analysis result to SQLite database."""
        created_at = get_current_utc_time().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO analyses (
                        symbol, timeframe, candle_time, analysis_time, current_price,
                        signal, confidence, entry, entry_zone_low, entry_zone_high,
                        stop_loss, take_profit_1, take_profit_2, take_profit_3,
                        risk_reward_tp1, risk_reward_tp2, risk_reward_tp3,
                        trend, trend_strength, momentum, volatility, setup_type,
                        support_zones, resistance_zones, invalidation_level,
                        bullish_scenario, bullish_probability, bearish_scenario, bearish_probability,
                        market_structure, reasoning, warnings, raw_gemini_response,
                        gemini_model, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?
                    )
                """, (
                    analysis.symbol, analysis.timeframe, analysis.candle_time, analysis.analysis_time, analysis.current_price,
                    analysis.signal, analysis.confidence, analysis.entry, analysis.entry_zone_low, analysis.entry_zone_high,
                    analysis.stop_loss, analysis.take_profit_1, analysis.take_profit_2, analysis.take_profit_3,
                    analysis.risk_reward_tp1, analysis.risk_reward_tp2, analysis.risk_reward_tp3,
                    analysis.trend, analysis.trend_strength, analysis.momentum, analysis.volatility, analysis.setup_type,
                    analysis.support_zones, analysis.resistance_zones, analysis.invalidation_level,
                    analysis.bullish_scenario, analysis.bullish_probability, analysis.bearish_scenario, analysis.bearish_probability,
                    analysis.market_structure, analysis.reasoning, analysis.warnings, analysis.raw_gemini_response,
                    analysis.gemini_model, created_at
                ))
                conn.commit()
                logger.info(f"DATABASE SAVED: Analysis for {analysis.symbol} {analysis.candle_time} ({analysis.signal}) saved successfully.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"DUPLICATE CANDLE: Analysis for {analysis.symbol} {analysis.candle_time} already exists in DB. Skipping.")
            return False
        except Exception as e:
            logger.error(f"Failed to save analysis to database: {e}")
            return False

    def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves latest analyses sorted by ID descending."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching recent analyses: {e}")
            return []
