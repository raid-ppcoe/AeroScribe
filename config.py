import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
EVENTS_LOG_PATH = LOGS_DIR / "events.jsonl"
ALERTS_LOG_PATH = LOGS_DIR / "alerts.jsonl"

# Audio Settings
WHISPER_MODEL_SIZE = "tiny.en"  # "tiny.en", "base.en", "small.en" - depending on CPU power
VAD_FILTER = True # Voice activity detection to ignore silence
CPU_THREADS = 4

# Airport Configuration (WSSS Changi mock layout)
AIRPORT_LAYOUT = {
    "runways": [
        "02L", "20R", "02C", "20C", "02R", "20L"
    ],
    "taxiways": [
        "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Victor"
    ],
    "platforms": [
        "Platform 1", "Platform 2", "Cargo", "Stand F42", "Terminal 1", "Terminal 2", "Terminal 3"
    ]
}

# Detection settings
CONFLICT_SEVERITY_HIGH = "HIGH"
CONFLICT_SEVERITY_MEDIUM = "MEDIUM"

# Server configuration
HOST = "0.0.0.0"
PORT = 8000


