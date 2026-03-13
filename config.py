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
WHISPER_MODEL_SIZE = "base.en"  # "tiny.en", "base.en", "small.en" - depending on CPU power
VAD_FILTER = True # Voice activity detection to ignore silence
CPU_THREADS = 4

# Airport Configuration (WSSS Changi mock layout)
AIRPORT_LAYOUT = {
    "runways": [
        "02L", "20R", "02C", "20C", "02R", "20L"
    ],
    "taxiways": [
        "Alpha", "Bravo", "Victor", "Whiskey", "North Cross", "South Cross"
    ],
    "platforms": [
        "Terminal 1", "Terminal 2", "Terminal 3", "Terminal 4", "Cargo", "Changi East"
    ]
}

# Detection settings
CONFLICT_SEVERITY_HIGH = "HIGH"
CONFLICT_SEVERITY_MEDIUM = "MEDIUM"

# Server configuration
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8080))

# Azure Foundry Configuration
AZURE_FOUNDRY_API_KEY = os.environ.get("AZURE_FOUNDRY_API_KEY", "")
AZURE_FOUNDRY_ENDPOINT = "https://aeroscribe-hackathon-reactor.cognitiveservices.azure.com/"
AZURE_FOUNDRY_MODEL = "gpt-4.1"

# Azure AI Content Safety Configuration (Responsible AI Governance)
AZURE_CONTENT_SAFETY_ENDPOINT = os.environ.get(
    "AZURE_CONTENT_SAFETY_ENDPOINT",
    "https://aeroscribe-hackathon-reactor.cognitiveservices.azure.com/"
)
AZURE_CONTENT_SAFETY_KEY = os.environ.get(
    "AZURE_CONTENT_SAFETY_KEY",
    AZURE_FOUNDRY_API_KEY  # Reuse the same key if co-located on the same Cognitive Services resource
)
