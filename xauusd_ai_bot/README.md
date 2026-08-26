# XAUUSD AI TRADING ANALYSIS BOT

Production-ready Python application that continuously monitors **XAUUSD (Gold/USD)**, fetches real-time and historical candle data from **BiQuote.io**, calculates key technical indicators, market structure, and price action patterns, prompts **Google Gemini AI** for structured technical trading analysis, independently validates all price levels and Risk/Reward ratios in Python, stores historical analysis records in **SQLite**, and dispatches alerts via **Telegram** during operating hours (10:00–20:00 Africa/Casablanca time).

---

> [!IMPORTANT]
> **NO AUTOMATED TRADING DISCLAIMER**
> - This application **NEVER** executes trades automatically.
> - It does **NOT** open, close, modify, or manage any trading positions.
> - It does **NOT** send trading orders or connect to broker execution endpoints.
> - The application is an **analytical and notification system only**. The user retains 100% manual discretion.

---

## 🏗 Architecture & Workflow

```
BiQuote.io API (GET /api/XAUUSD & /api/XAUUSD/ohlc)
       │
       ▼
Real-time Quote & M5 Closed Candles (isOpen == False)
       │
       ▼
Strict Data Validation & Staleness Check (max 300s)
       │
       ▼
Python Technical Indicators (EMA20/50/200, RSI14, MACD, ATR14, ADX14, Stochastic)
       │
       ▼
Price Action & Market Structure (Swing Highs/Lows, Engulfing, Pin Bars, S/R Zones)
       │
       ▼
Google Gemini AI Prompting (Structured Pydantic Output)
       │
       ▼
Python Signal & Price Relationship Validation + Risk/Reward Calculations
       │
       ▼
Deduplication & SQLite Database Persistence (xauusd_ai.db)
       │
       ▼
Telegram Notification Dispatcher (Formatted HTML Output)
```

---

## 📦 Project Structure

```
xauusd_ai_bot/
├── main.py                # Main application entry point & startup health checks
├── config.py              # Configuration & environment variable loader
├── logger.py              # Centralized logging setup (console + logs/bot.log)
├── utils.py               # Timezone formatting (Africa/Casablanca) & helpers
├── models.py              # Pydantic schemas (Quote, CandleBar, Gemini, Analysis)
├── biquote_client.py      # HTTP client for BiQuote.io quote & OHLC API
├── market_data.py         # Market data validator & DataFrame normalizer
├── indicators.py          # Python calculation of EMA, RSI, MACD, ATR, ADX, Stoch
├── price_action.py        # Candlestick pattern detection & volatility features
├── market_structure.py    # Swing pivot detection, BOS, CHOCH, and Trend analysis
├── support_resistance.py  # Support & Resistance zone clustering algorithm
├── gemini_client.py       # Google Gemini SDK interface & structured JSON prompting
├── signal_validator.py    # Python price hierarchy, confidence filter & RR calculator
├── database.py            # SQLite database manager & candle deduplication
├── telegram_bot.py        # Telegram bot message formatter & dispatcher
├── scheduler.py           # Timezone-aware 5-min interval scheduler (10:00-20:00)
├── dashboard.py           # Streamlit web dashboard for live monitoring
├── requirements.txt       # Dependencies manifest
├── .env.example           # Template for environment variables
├── .gitignore             # Git exclusion rules
├── README.md              # System documentation
└── tests/                 # Unit test suite
    ├── test_models.py
    ├── test_market_data.py
    ├── test_indicators.py
    ├── test_price_action.py
    ├── test_signal_validator.py
    ├── test_database.py
    └── test_scheduler.py
```

---

## 🛠 Prerequisites & Installation

### Requirements
- Python 3.11 or higher
- Git

### 1. Clone & Navigate to Repository
```bash
git clone <repository-url>
cd xauusd_ai_bot
```

### 2. Create Virtual Environment & Install Dependencies
**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration (`.env`)

Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```

Edit `.env` with your actual API keys and credentials:

```ini
# BiQuote API Configuration
BIQUOTE_BASE_URL=https://biquote.io/api
SYMBOL=XAUUSD
TIMEFRAME=5m
CANDLE_COUNT=200
MAX_QUOTE_AGE_SECONDS=300

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
MIN_CONFIDENCE=70

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Scheduling & Timezone Configuration
TIMEZONE=Africa/Casablanca
WORK_START_HOUR=10
WORK_END_HOUR=20

# Database Configuration
DB_PATH=xauusd_ai.db
```

---

## 🚀 Running the Bot

### Normal Scheduled Execution
Runs continuously according to the 5-minute candle schedule between 10:00 and 20:00 Morocco time (`Africa/Casablanca`).
```bash
python main.py
```

### Run Single Immediate Cycle (Dry Run / Testing)
Executes one analysis cycle immediately and exits:
```bash
python main.py --once
```

### Bypass Schedule Lock for Testing Outside Working Hours
Runs continuous 5-minute cycles regardless of local time:
```bash
python main.py --ignore-schedule
```

---

## 📊 Streamlit Interactive Dashboard

To launch the web dashboard:
```bash
streamlit run dashboard.py
```
Open your browser at `http://localhost:8501` to view live XAUUSD prices, current quote staleness, recent AI analysis records, technical indicator summaries, and signal history.

---

## 🧪 Running Unit Tests

Execute pytest across the full test suite:
```bash
pytest tests/ -v
```

---

## 🪟 Windows Automatic Startup Deployment

### Option A: Windows Startup Folder (Recommended for Desktop)
1. Create a script named `run_bot.bat` inside the project folder:
```bat
@echo off
cd /d "C:\path\to\xauusd_ai_bot"
call .venv\Scripts\activate.bat
python main.py
```
2. Press `Win + R`, type `shell:startup`, and press Enter.
3. Create a shortcut to `run_bot.bat` inside the Startup folder.

### Option B: Windows Task Scheduler (Recommended for Servers)
1. Open **Task Scheduler** in Windows.
2. Click **Create Task...**
3. Under **General**:
   - Name: `XAUUSD_AI_Bot`
   - Select *Run whether user is logged on or not*.
4. Under **Triggers**:
   - Begin the task: *At startup*.
5. Under **Actions**:
   - Action: *Start a program*.
   - Program/script: `C:\path\to\xauusd_ai_bot\.venv\Scripts\python.exe`
   - Add arguments: `main.py`
   - Start in: `C:\path\to\xauusd_ai_bot\`
6. Click **OK** to save.

---

## 🔧 Configuration Customization

- **Change Instrument / Symbol**: Modify `SYMBOL` in `.env` (e.g., `GOLD`, `XAUUSD.a`).
- **Change Timeframe**: Modify `TIMEFRAME` in `.env` (e.g., `15m`, `1h`).
- **Change Schedule Hours**: Modify `WORK_START_HOUR` and `WORK_END_HOUR` in `.env`.
- **Change Confidence Cutoff**: Modify `MIN_CONFIDENCE` in `.env` (default: `70`).
- **Change Gemini Model**: Modify `GEMINI_MODEL` in `.env` (e.g., `gemini-2.5-flash` or `gemini-1.5-pro`).
