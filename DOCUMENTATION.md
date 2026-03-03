# AeroScribe: Comprehensive System Documentation

## 1. Project Overview
AeroScribe (formerly ATC AI Assist System) is a real-time, offline, and CPU-compatible decision-support layer for Air Traffic Control. This system converts radio speech into structured ATC events, maintains an active operational state of aircraft and ground vehicles, and automatically detects conflicts (e.g., runway incursions) and emergency escalations.

It is designed to be highly resilient, running completely locally without reliance on paid cloud APIs or GPUs.

---

## 2. Core Components & Architecture

### 2.1 Audio Processing (`audio/`)
This module handles the ingestion and transcription of audio.
- **`speech_listener.py`**: Handles microphone input or `.wav` file ingestion. It relies on the `sounddevice` library for robust, cross-platform audio capturing, streaming audio in configurable chunks.
- **`stt_engine.py`**: Employs `faster-whisper` for fast, CPU-only local transcription of audio chunks sent by the listener.
- **`atc_parser.py`**: Provides initial regex and keyword-based parsing logic as a fallback or heuristic extractor for specific entities, though the heavy lifting is handled by the LLM.

### 2.2 LLM Processing Agent (`agent/`)
- **`llm_processor.py`**: Utilizes a highly efficient, CPU-friendly Hugging Face model (`Qwen/Qwen2.5-0.5B-Instruct`) to interpret transcripts.
  - Takes the raw STT text and output JSON mapping the entity state (e.g., aircraft ID, destination runway, intent).
  - Handles the complex logic of mapping fuzzy, phonetically inaccurate transcription text to strict operational schemas based on the current airport layout state.

### 2.3 Operational State Management (`state/`)
This module acts as the source of truth for all entities on the airfield.
- **`aircraft_state.py`**: Tracks the dynamic state of airborne or taxiing aircraft, updating properties like current segment, destination, and clearance state based on processed LLM events.
- **`ground_state.py`**: Manages ground vehicles (e.g., tugs, fire tenders, ambulances) on platforms and taxiways.
- **`event_store.py`**: Provides event-sourced logging functionality. All transcripts, state snapshots, parsed events, and alerts are durably appended to JSONL log files (`logs/events.jsonl`, `logs/alerts.jsonl`) for replayability and audit trails.

### 2.4 Detection & Alerting (`detection/`)
- **`conflict_detection.py`**: Continuously monitors the state engines to detect unsafe conditions using deterministic rules:
  - Unauthorized runway incursions
  - Multiple entities cleared on the same runway
  - Taxiway segment overlaps
  - Unapproved movements or clearance violations
- **`emergency_detection.py`**: Monitors for emergency flags raised by the LLM (based on phrases like "mayday", "fire", or "engine failure") and immediate scales alerts.

### 2.5 Live Dashboard (`dashboard/`)
- **`server.py`**: A FastAPI application that provides the WebSocket server.
- **`templates/dashboard.html`**: The vanilla HTML/JS/CSS frontend. It connects to the WebSocket to consume and display `transcript`, `state`, and `alert` events in real-time. It features a responsive, glassmorphic UI.

### 2.6 Simulation Engine (`simulation/`)
- **`radio_simulator.py`**: A powerful testing harness that injects pre-scripted radio calls into the pipeline without needing a live microphone. It supports:
  - **Normal Mode**: Standard arrival and departure flows.
  - **Emergency Mode**: Tests extreme edge cases, simulating a rejected takeoff, engine fire, MAYDAY calls, and the dispatch of emergency response vehicles.

---

## 3. Technology Stack
- **Backend Framework**: FastAPI (Uvicorn, WebSockets)
- **Audio Capturing**: `sounddevice`
- **Transcription**: `faster-whisper`
- **Natural Language Understanding**: `transformers` (`Qwen/Qwen2.5-0.5B-Instruct` via pipeline)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (WebSocket Client)
- **Testing**: `pytest`

---

## 4. Setup & Installation

The system is designed to run locally on Windows, macOS, or Linux. Python 3.10+ is recommended.

1. **Clone the repository** and navigate to the project directory.
2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Running the Application

### 5.1 Simulation Mode (Recommended for Development)
To run the system without a microphone using the built-in scripted scenarios:
```bash
python main.py --simulate
```
For testing emergency escalation paths:
```bash
python main.py --simulate-emergency
```
*Access the dashboard at: http://127.0.0.1:8080*

### 5.2 Live Microphone Mode
To transcribe and process your own live voice commands:
```bash
python main.py
```

### 5.3 Offline WAV File processing
To run the system on a pre-recorded audio file:
```bash
python main.py --demo-wav path/to/audio.wav
```

---

## 6. Challenges Faced During Development

Building a real-time, local, and resilient AI system introduced several distinct engineering challenges:

### 6.1 Audio Capture & Native Dependencies
**Challenge**: Initially, the project relied on `pyaudio` for microphone capture. This created massive friction during installation, especially on newer Python versions (3.12+) and Windows machines, where missing C++ build tools or lack of pre-compiled wheels caused installations to fail completely.
**Solution**: Migrated the audio ingestion pipeline to use `sounddevice`. This abstraction proved significantly more reliable across OS environments and avoided the `pyaudio` compilation nightmares, resulting in a smoother developer and user setup experience.

### 6.2 CPU-Bound Performance Constraints
**Challenge**: The system needed to perform real-time Speech-to-Text (STT) and Large Language Model (LLM) processing sequentially, strict local execution, without relying on a GPU. Standard Whisper models and 7B+ parameter LLMs took too long to infer, causing severe latency between an ATC command and the UI update.
**Solution**:
1. Implemented `faster-whisper` for optimized CTranslate2 CPU execution.
2. Selected `Qwen/Qwen2.5-0.5B-Instruct`—a highly optimized, sub-1-billion parameter model—for the LLM parser. This allowed the system to parse transcripts into structured JSON rapidly on standard CPU threads, achieving acceptable real-time latency.

### 6.3 STT Hallucinations & Phonetic Errors
**Challenge**: Working in a noisy acoustic environment (aviation simulation) with smaller STT models leads to frequent phonetic misspellings. Crucial emergency phrases like "MAYDAY" were occasionally transcribed as "maybe", "may day", or "made a". Standard regex parsers would fail to catch these, potentially missing critical emergencies.
**Solution**: Designed a resilient prompting pipeline for the LLM. Instead of expecting perfect text, the LLM prompt explicitly warns the model about STT phonetic spelling errors. It is instructed to use contextual clues (e.g., words related to fire, rejection, or failure) alongside phonetic similarities to correctly infer intent and raise the `emergency_flag`.

### 6.4 Real-time State Synchronization
**Challenge**: Managing the concurrency of streaming audio transcription, LLM processing, deterministic rules engine (conflict detection), and the FastAPI web server. Ensuring the UI correctly reflected the state without race conditions or missed events.
**Solution**: Implemented a decoupled architecture using WebSockets (`broadcast_sync`). The core text processing pipeline modifies an in-memory `AircraftStateEngine` and `GroundStateEngine`. After processing, it synchronously blasts full state snapshots and alerts to all connected WebSocket clients, ensuring the dashboard remains durably consistent with the backend state. Event-sourced logging was also implemented for auditability.

### 6.5 The Scripted Simulator Testing Burden
**Challenge**: Testing the LLM state modifications manually required repeatedly speaking into the microphone, which was exhausting, inconsistent, and slow for iterative development.
**Solution**: Built the `radio_simulator.py` component to inject perfect transcripts at timed intervals. This drastically improved the iteration lifecycle and allowed for reliable, reproducible testing of edge-case scenarios like the complex emergency towing sequence.
