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

class LLMProcessor:
    def __init__(self):
        try:
            from transformers import pipeline
            import torch
            
            # Using a very small, fast instruction model that can run locally on CPU
            model_id = "Qwen/Qwen2.5-0.5B-Instruct" 
            logger.info(f"Loading local Hugging Face model: {model_id}...")
            
            self.pipe = pipeline(
                "text-generation", 
                model=model_id, 
                torch_dtype=torch.float32, 
                device_map="auto"
            )
            logger.info("Local LLM initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face pipeline: {e}")
            self.pipe = None

    def process(self, transcript: str, current_state: Dict[str, Any]) -> LLMResponse:
        fallback_resp = LLMResponse(
            parsed_event=EntityUpdate(
                entity_id="UNKNOWN", 
                entity_type="unknown", 
                intent="unknown", 
                route=[], 
                clearance_state="pending", 
                emergency_flag=False
            ), 
            alerts=[]
        )
        
        if not self.pipe:
            logger.warning("Local LLM not loaded. Returning fallback.")
            return fallback_resp

        system_prompt = f"""You are an Air Traffic Control AI parsing transcripts at WSSS airport.
Airport Layout: {json.dumps(config.AIRPORT_LAYOUT)}

Task:
1. Parse the transcript to identify entity (aircraft/vehicle), intent, route, runway, etc.
2. Compare with `current_state` to find conflicts or emergencies.
3. Determine clearance (granted or pending).
4. Output strict JSON matching this schema:
{{
  "parsed_event": {{
    "entity_id": "string",
    "entity_type": "aircraft or vehicle",
    "intent": "str",
    "route": ["str"],
    "runway": "str or null",
    "destination": "str or null",
    "clearance_state": "granted or pending",
    "emergency_flag": bool
  }},
  "alerts": [
    {{
      "alert_type": "str",
      "severity": "HIGH or MEDIUM",
      "entities": ["str"],
      "message": "str"
    }}
  ]
}}

Current State:
{json.dumps(current_state)}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript: {transcript}\n\nProvide the JSON output:"}
        ]
        
        try:
            outputs = self.pipe(
                messages, 
                max_new_tokens=512, 
                do_sample=False,
                return_full_text=False
            )
            
            text_out = outputs[0]["generated_text"]
            
            # Extract JSON from potential markdown wrapping
            json_match = re.search(r'```json\s*(.*?)\s*```', text_out, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Attempt to parse raw if no backticks
                json_str = text_out
                
            return LLMResponse.model_validate_json(json_str)
            
        except Exception as e:
            logger.error(f"Local LLM Processing error: {e}")
            return fallback_resp
