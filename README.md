# AeroScribe ✈️

A real-time, **multi-agent** decision-support layer for Air Traffic Control powered by **Microsoft Azure AI Foundry**. This system converts radio speech into structured ATC events via a 4-agent orchestration pipeline, maintains an active operational state of aircraft and ground vehicles, and automatically detects conflicts and emergency escalations. It integrates **Azure AI Content Safety** for Responsible AI governance and exposes its capabilities via a **Model Context Protocol (MCP) server**.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Azure](https://img.shields.io/badge/Azure-AI%20Foundry-0078D4.svg)
![MCP](https://img.shields.io/badge/MCP-Server-blueviolet.svg)

## Features
- **Multi-Agent Orchestration:** 4-agent pipeline powered by Azure AI Foundry (GPT-4.1):
  - **ContentSafetyAgent**: Screens transcripts via Azure AI Content Safety (Responsible AI)
  - **TranscriptionAgent**: Phonetically-resilient STT-to-aviation-JSON mapping
  - **SafetyAgent**: Audits events against the airport digital twin for conflict detection
  - **StrategicPlanningAgent**: On-demand conflict-free routing suggestions
- **MCP Server:** Model Context Protocol server exposing airport state, layout, and alerts as discoverable tools for external agents (e.g., VS Code Copilot).
- **Audio Intelligence (STT & NLP):** Uses `faster-whisper` for fast, CPU-only local transcription.
- **State Management Engine:** In-memory object tracking of Aircraft and Ground vehicles.
- **Event-Sourced Logging:** All transcripts, parsed events, state snapshots, and alerts are appended to JSONL files for easy history replay.
- **Real-time Conflict Detection:** Deterministic rules alert on unauthorized runway incursions, taxiway overlaps, and clearance violations.
- **Emergency Escalation:** Detects keywords like "mayday", "fire", and "engine failure" and immediately alerts the dashboard.
- **WebSockets Dashboard:** A glassmorphic, dynamic, and responsive UI built with FastAPI, WebSockets, and vanilla HTML/JS/CSS.
- **Simulation Engine:** Scripted radio simulator to dry-run logic and test the dashboard without speaking into a microphone.
- **Azure Deployment:** One-command deployment to Azure App Service via `deploy_azure.sh`.

---

##  System Architecture

```text
aerscribe/
├── main.py                          # Entry point (Server, STT Listener, Simulator)
├── config.py                        # Airport layout, Azure Foundry & Content Safety settings
├── mcp_server.py                    # MCP Server (Model Context Protocol)
├── requirements.txt                 # Python dependencies
├── deploy_azure.sh                  # Azure App Service deployment script
├── audio/
│   ├── speech_listener.py           # Chunking mic/wav input
│   ├── stt_engine.py                # Local Faster-Whisper execution
│   └── atc_parser.py                # NLP regex intent extraction
├── agent/
│   └── llm_processor.py             # Multi-Agent Orchestrator (4-agent pipeline)
├── state/
│   ├── event_store.py               # JSONL logging utility
│   ├── aircraft_state.py            # Tracks airborne/taxiing aircraft
│   └── ground_state.py              # Tracks vehicles and platform movements
├── detection/
│   ├── conflict_detection.py        # Runway & Taxiway deterministic alerts
│   └── emergency_detection.py       # Emergency escalation rules
├── dashboard/
│   ├── server.py                    # FastAPI & WebSocket manager
│   └── templates/
│       ├── dashboard.html           # Live operational UI
│       └── emergency.html           # Emergency services interface
├── simulation/
│   └── radio_simulator.py           # Scripted mock-ATC scenario
├── logs/                            # Automatically generated events.jsonl & alerts.jsonl
└── tests/                           # Pytest unit testing suite
```

---

##  Setup Instructions

This system is designed to run locally on **macOS** or **Windows** without requiring any paid cloud APIs or GPUs.

**1. Clone or Open the Project**
Navigate into the `atc_ai_assist` directory.

**2. Create a Virtual Environment**
```bash
python -m venv venv
```

**3. Activate the Environment**
- **Windows:**
  ```powershell
  .\venv\Scripts\Activate
  ```
- **macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

**4. Install Dependencies**
```bash
pip install -r requirements.txt
```
---

##  How to Run

### Mode 1: Simulation (Recommended for Testing)
Because streaming audio locally can require specific native C++ headers, the easiest way to see the engine in action is via the built-in simulator. It feeds pre-scripted radio calls into the logic layer at set intervals.

```bash
python main.py --simulate
```
*Wait a few seconds for the engine to load, then open your browser to:*
 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### Mode 2: Live Microphone
*Note: This relies on `pyaudio`. See the Troubleshooting section below if you have installation errors.*
```bash
python main.py
```
*Speak clearly into your default system microphone. (e.g., "Tower, Spartan 1 requesting taxi to Runway 09L.")*

### Mode 3: Unit Testing
To run the automated test suite evaluating the parser rules, state updates, and conflict logic:
```bash
pytest tests/
```

---

## Troubleshooting

**"Failed building wheel for pyaudio" / "Microsoft Visual C++ 14.0 or greater is required"**
If you are running the newest versions of Python (e.g., Python 3.12, 3.13, 3.14) on Windows, the pre-built wheels for `pyaudio` may not exist yet, and pip will try to compile it from source.
- **Solution A:** Install the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
- **Solution B:** Run the app in Simulation Mode (`python main.py --simulate`), which bypasses the need for local microphone packages entirely!
- **Solution C:** Use an older, stable version of Python (e.g., Python 3.10 or 3.11) where wheels are readily available.

**"No module named 'uvicorn'"**
If you run the app and see missing module errors, ensure your virtual environment is actively sourced (`.\venv\Scripts\Activate`) and that `pip install -r requirements.txt` completed without errors.
