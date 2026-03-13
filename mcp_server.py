"""
AeroScribe MCP Server
=====================
A Model Context Protocol (MCP)-compatible server that exposes AeroScribe's
airport state, layout, and alerts as discoverable tools for external agents.

This implementation uses FastAPI to create MCP-compatible REST endpoints,
following the MCP tool discovery and invocation patterns.

Run standalone:
    python mcp_server.py

Or mount alongside the main dashboard (already integrated via main.py).
"""

import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config

logger = logging.getLogger(__name__)

# ─── MCP Tool Registry ───────────────────────────────────────────────────────

class MCPToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[MCPToolParameter] = []

class MCPToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}

class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]

# ─── MCP Server App ──────────────────────────────────────────────────────────

mcp_app = FastAPI(
    title="AeroScribe MCP Server",
    description="Model Context Protocol server exposing ATC airport state, layout, and alerts as discoverable tools.",
    version="1.0.0"
)

# Tool definitions registry
TOOLS: List[MCPToolDefinition] = [
    MCPToolDefinition(
        name="get_airport_layout",
        description="Returns the static configuration of WSSS Changi airport including all runways, taxiways, and terminal platforms.",
        parameters=[]
    ),
    MCPToolDefinition(
        name="get_airport_state",
        description="Returns the latest snapshot of all tracked aircraft and ground vehicles from the event log.",
        parameters=[]
    ),
    MCPToolDefinition(
        name="get_live_alerts",
        description="Returns the most recent alerts (conflicts, emergencies, content safety flags) from the alerts log.",
        parameters=[
            MCPToolParameter(name="count", type="integer", description="Number of recent alerts to return (default: 10)", required=False)
        ]
    ),
]

# ─── Tool Implementations ────────────────────────────────────────────────────

def _tool_get_airport_layout() -> str:
    return json.dumps(config.AIRPORT_LAYOUT, indent=2)

def _tool_get_airport_state() -> str:
    try:
        if config.EVENTS_LOG_PATH.exists():
            with open(config.EVENTS_LOG_PATH, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return json.dumps({"status": "empty", "message": "State log is empty."})
                # Find the most recent line that contains state
                for line in reversed(lines):
                    try:
                        data = json.loads(line)
                        if "state" in data:
                            return json.dumps(data["state"], indent=2)
                    except json.JSONDecodeError:
                        continue
        return json.dumps({"status": "no_data", "message": "No state data available."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def _tool_get_live_alerts(count: int = 10) -> str:
    try:
        if config.ALERTS_LOG_PATH.exists():
            with open(config.ALERTS_LOG_PATH, 'r') as f:
                lines = f.readlines()
                recent = lines[-count:] if len(lines) >= count else lines
                alerts = []
                for line in recent:
                    try:
                        alerts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                return json.dumps(alerts, indent=2)
        return json.dumps({"status": "no_alerts", "message": "No alerts found."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

TOOL_HANDLERS = {
    "get_airport_layout": lambda args: _tool_get_airport_layout(),
    "get_airport_state": lambda args: _tool_get_airport_state(),
    "get_live_alerts": lambda args: _tool_get_live_alerts(args.get("count", 10)),
}

# ─── MCP Protocol Endpoints ──────────────────────────────────────────────────

@mcp_app.get("/mcp/tools", summary="List available MCP tools")
async def list_tools():
    """MCP Tool Discovery: Returns all available tools and their schemas."""
    return {"tools": [t.dict() for t in TOOLS]}

@mcp_app.post("/mcp/tools/call", summary="Invoke an MCP tool")
async def call_tool(request: MCPToolCallRequest):
    """MCP Tool Invocation: Calls a tool by name with the provided arguments."""
    handler = TOOL_HANDLERS.get(request.name)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Tool '{request.name}' not found.")
    
    result = handler(request.arguments)
    return MCPToolCallResponse(content=[{"type": "text", "text": result}])

@mcp_app.get("/mcp/info", summary="MCP Server Info")
async def server_info():
    """Returns metadata about this MCP server."""
    return {
        "name": "AeroScribe ATC Server",
        "version": "1.0.0",
        "description": "Exposes real-time ATC airport state, layout, and safety alerts for multi-agent orchestration.",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AeroScribe MCP Server on port 8001...")
    uvicorn.run(mcp_app, host="0.0.0.0", port=8001, log_level="info")
