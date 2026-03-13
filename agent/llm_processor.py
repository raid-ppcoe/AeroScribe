import json
import logging
import re
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
import config

logger = logging.getLogger(__name__)

class Alert(BaseModel):
    alert_type: str
    severity: str
    entities: List[str]
    message: str

class EntityUpdate(BaseModel):
    entity_id: str
    entity_type: str
    intent: Optional[str] = "unknown"
    route: Optional[List[str]] = []
    destination: Optional[str] = None
    runway: Optional[str] = None
    clearance_state: Optional[str] = "pending"
    emergency_flag: Optional[bool] = False

class LLMResponse(BaseModel):
    parsed_event: EntityUpdate
    alerts: List[Alert]

class BaseAgent:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

class TranscriptionAgent(BaseAgent):
    """Specialized in mapping phonetically noisy STT to aviation JSON."""
    def process(self, transcript: str) -> EntityUpdate:
        system_prompt = f"""You are an expert ATC Transcription Agent.
        The input is a noisy STT transcript of aviation radio. 
        Map it to a structured JSON event. Use contextual phonetic inference.
        Example: 'maybe' or 'made a' in a dangerous context = MAYDAY.
        Airport Layout: {json.dumps(config.AIRPORT_LAYOUT)}
        
        Output JSON:
        {{
            "entity_id": "string",
            "entity_type": "aircraft or vehicle",
            "intent": "string",
            "route": ["string"],
            "runway": "string or null",
            "destination": "string or null",
            "clearance_state": "granted or pending",
            "emergency_flag": bool
        }}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript: {transcript}"}
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={ "type": "json_object" }
            )
            return EntityUpdate.model_validate_json(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"TranscriptionAgent error: {e}")
            return EntityUpdate(entity_id="UNKNOWN", entity_type="unknown")

class SafetyAgent(BaseAgent):
    """Detects high-stakes violations and conflicts against the airport digital twin."""
    def audit(self, parsed_event: EntityUpdate, current_state: Dict[str, Any]) -> List[Alert]:
        system_prompt = f"""You are an ATC Safety Auditor. 
        Analyze the proposed event against the current airport state for safety violations.
        Current State: {json.dumps(current_state)}
        
        Output a JSON list of alerts:
        [{{ "alert_type": "string", "severity": "HIGH or MEDIUM", "entities": ["string"], "message": "string" }}]
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Proposed Event: {parsed_event.model_dump_json()}"}
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            # Handle if the model returns a wrapper object or a direct list
            alerts_data = data.get("alerts", data) if isinstance(data, dict) else data
            return [Alert(**a) for a in alerts_data]
        except Exception as e:
            logger.error(f"SafetyAgent error: {e}")
            return []

class StrategicPlanningAgent(BaseAgent):
    """Generates routing suggestions and long-term plans."""
    def generate_plan(self, current_state: Dict[str, Any]) -> str:
        system_prompt = f"""You are an ATC Strategic Planner.
        Analyze the state and provide a safe routing suggestion for all active entities.
        Airport Layout: {json.dumps(config.AIRPORT_LAYOUT)}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current State: {json.dumps(current_state)}"}
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"StrategicPlanningAgent error: {e}")
            return "Unable to generate plan."

class ContentSafetyAgent:
    """Screens transcripts using Azure AI Content Safety for Responsible AI governance."""
    def __init__(self):
        self.client = None
        try:
            from azure.ai.contentsafety import ContentSafetyClient
            from azure.core.credentials import AzureKeyCredential
            self.client = ContentSafetyClient(
                endpoint=config.AZURE_CONTENT_SAFETY_ENDPOINT,
                credential=AzureKeyCredential(config.AZURE_CONTENT_SAFETY_KEY)
            )
            logger.info("ContentSafetyAgent initialized.")
        except Exception as e:
            logger.warning(f"ContentSafetyAgent could not initialize (non-fatal): {e}")

    def screen(self, text: str) -> Dict[str, Any]:
        """Screen text for harmful content. Returns a dict with 'safe' bool and 'details'."""
        if not self.client:
            return {"safe": True, "details": "Content Safety not available, skipping."}
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
            request = AnalyzeTextOptions(text=text)
            response = self.client.analyze_text(request)
            
            # Check if any category has severity > 2 (scale 0-6)
            flagged_categories = []
            for category_result in response.categories_analysis:
                if category_result.severity and category_result.severity > 2:
                    flagged_categories.append({
                        "category": category_result.category,
                        "severity": category_result.severity
                    })
            
            if flagged_categories:
                logger.warning(f"Content Safety flagged transcript: {flagged_categories}")
                return {"safe": False, "details": flagged_categories}
            
            return {"safe": True, "details": "Passed all content safety checks."}
        except Exception as e:
            logger.error(f"ContentSafetyAgent screening error: {e}")
            return {"safe": True, "details": f"Screening error (fail-open): {e}"}

class AeroScribeOrchestrator:
    """Orchestrates multiple specialized agents using Microsoft Foundry.
    
    Pipeline:
      0. ContentSafetyAgent   – Screens raw transcript for harmful content (Responsible AI)
      1. TranscriptionAgent   – Parses noisy STT text into structured aviation JSON
      2. SafetyAgent          – Audits parsed event against the airport digital twin
      3. StrategicPlanningAgent – (on-demand) Generates conflict-free routing suggestions
    """
    def __init__(self):
        # Initialize Content Safety Agent (independent of Azure OpenAI)
        self.content_safety_agent = ContentSafetyAgent()
        
        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                azure_endpoint=config.AZURE_FOUNDRY_ENDPOINT,
                api_key=config.AZURE_FOUNDRY_API_KEY,
                api_version="2025-01-01-preview"
            )
            self.model_name = config.AZURE_FOUNDRY_MODEL
            
            # Initialize specialized agents
            self.transcription_agent = TranscriptionAgent(self.client, self.model_name)
            self.safety_agent = SafetyAgent(self.client, self.model_name)
            self.planning_agent = StrategicPlanningAgent(self.client, self.model_name)
            
            logger.info("AeroScribeOrchestrator initialized with 4-agent pipeline.")
        except Exception as e:
            logger.error(f"Failed to initialize Orchestrator: {e}")
            self.client = None

    def process(self, transcript: str, current_state: Dict[str, Any]) -> LLMResponse:
        if not self.client:
            return LLMResponse(
                parsed_event=EntityUpdate(entity_id="UNKNOWN", entity_type="unknown"),
                alerts=[]
            )
        
        # Step 0: Content Safety Agent screens the raw transcript
        safety_result = self.content_safety_agent.screen(transcript)
        if not safety_result["safe"]:
            logger.warning(f"Transcript blocked by Content Safety: {safety_result['details']}")
            return LLMResponse(
                parsed_event=EntityUpdate(entity_id="BLOCKED", entity_type="unknown", intent="content_blocked"),
                alerts=[Alert(
                    alert_type="CONTENT_SAFETY",
                    severity="HIGH",
                    entities=[],
                    message=f"Transcript blocked by Responsible AI filter: {safety_result['details']}"
                )]
            )
        
        # Step 1: Transcription Agent parses the raw text
        parsed_event = self.transcription_agent.process(transcript)
        
        # Step 2: Safety Agent audits the result for conflicts
        alerts = self.safety_agent.audit(parsed_event, current_state)
        
        return LLMResponse(parsed_event=parsed_event, alerts=alerts)

    def generate_plan(self, current_state: Dict[str, Any]) -> str:
        if not self.client:
            return "Orchestrator not initialized."
        return self.planning_agent.generate_plan(current_state)

# Keep for backward compatibility with main.py during refactor
LLMProcessor = AeroScribeOrchestrator
