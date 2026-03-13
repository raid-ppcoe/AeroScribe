import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import logging
from pathlib import Path
import config

logger = logging.getLogger(__name__)

app = FastAPI(title="ATC AI Assist Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory pub-sub for broadcasting to clients
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.state_cache = None
        self.transcript_cache = []
        self.alert_cache = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Flush the recent history cache to new clients so they don't see an empty screen
        if self.state_cache:
            try:
                await websocket.send_text(self.state_cache)
            except:
                pass
        
        for msg in self.transcript_cache:
            try:
                await websocket.send_text(msg)
            except:
                pass
                
        for msg in self.alert_cache:
            try:
                await websocket.send_text(msg)
            except:
                pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def _update_cache(self, msg: str):
        try:
            data = json.loads(msg)
            topic = data.get("topic")
            
            if topic == "state":
                self.state_cache = msg
            elif topic == "transcript":
                self.transcript_cache.append(msg)
                if len(self.transcript_cache) > 15:
                    self.transcript_cache.pop(0)
            elif topic == "transcript_update":
                # Find the existing transcript with this ID and update it in cache
                target_id = data.get("data", {}).get("id")
                for i in range(len(self.transcript_cache)):
                    cached_data = json.loads(self.transcript_cache[i])
                    if cached_data.get("data", {}).get("id") == target_id:
                        # Replace the raw broadcast with the updated one
                        data["topic"] = "transcript" # Send it to new clients as a normal transcript
                        self.transcript_cache[i] = json.dumps(data)
                        break
            elif topic == "alert":
                self.alert_cache.append(msg)
                if len(self.alert_cache) > 10:
                    self.alert_cache.pop(0)
        except Exception as e:
            logger.error(f"Cache error: {e}")

    async def broadcast(self, message: str):
        self._update_cache(message)
        # Create a copy to gracefully handle disconnections during broadcast
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                self.disconnect(connection)

manager = ConnectionManager()
_main_loop = None

def broadcast_sync(topic: str, data: dict):
    """
    Called from other threads to push data to the asyncio loop.
    Since main processing happens in background threads, we inject into the 
    FastAPI event loop.
    """
    global _main_loop
    if _main_loop is None:
        return
        
    msg = json.dumps({"topic": topic, "data": data})
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg), _main_loop)
    except Exception as e:
        logger.error(f"Failed to schedule broadcast: {e}")

@app.get("/")
async def get_dashboard():
    # Load dashboard.html
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
            # A simple hack to inject the local IP dynamically if needed, 
            # but we're mostly relying on JS location.host for now.
        return HTMLResponse(html)
    except FileNotFoundError:
        return HTMLResponse("<h1>Dashboard Template Missing</h1>", status_code=404)

@app.get("/emergency")
async def get_emergency_dashboard():
    template_path = Path(__file__).parent / "templates" / "emergency.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        return HTMLResponse(html)
    except FileNotFoundError:
        return HTMLResponse("<h1>Emergency Template Missing</h1>", status_code=404)

# In-memory store for actions taken on incidents (timestamp -> action)
incident_actions = {}

class EmergencyNotification(BaseModel):
    message: str
    entities: list[str]
    severity: str
    timestamp: float

@app.post("/api/notify-emergency")
async def notify_emergency(payload: EmergencyNotification):
    # Broadcast the notification to all clients, specifically meant for emergency.html
    broadcast_sync("emergency_notification", payload.dict())
    return {"status": "success", "message": "Emergency broadcast sent"}

@app.get("/api/incident-logs")
async def get_incident_logs():
    """Returns all past alerts from the logs file, enhanced with action status."""
    alerts = []
    log_path = config.ALERTS_LOG_PATH
    
    if log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        alert = json.loads(line)
                        ts = str(alert.get("timestamp"))
                        alert["action_status"] = incident_actions.get(ts, "pending")
                        alerts.append(alert)
        except Exception as e:
            logger.error(f"Error reading incident logs: {e}")
            
    # Return most recent first
    return sorted(alerts, key=lambda x: x.get("timestamp", 0), reverse=True)

class IncidentAction(BaseModel):
    action: str # "notified" or "dismissed"

@app.post("/api/incident-logs/{timestamp}/action")
async def record_incident_action(timestamp: str, payload: IncidentAction):
    """Records an approve/dismiss action for a specific incident."""
    incident_actions[timestamp] = payload.action
    return {"status": "success", "timestamp": timestamp, "action": payload.action}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from the client in this one-way feed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
