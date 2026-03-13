import time
from typing import Dict, Any, List
import config

class EmergencyDetector:
    def __init__(self, aircraft_engine, ground_engine):
        self.aircraft_engine = aircraft_engine
        self.ground_engine = ground_engine
        self.alerted_entities = set()
        
    def detect_emergencies(self) -> List[Dict[str, Any]]:
        alerts = []
        ac_snap = self.aircraft_engine.get_snapshot()
        gnd_snap = self.ground_engine.get_snapshot()
        
        for eid, ac in ac_snap.items():
            if ac.get("emergency_flag"):
                if eid not in self.alerted_entities:
                    self.alerted_entities.add(eid)
                    alerts.append({
                        "alert_type": "EMERGENCY_DECLARED",
                        "severity": config.CONFLICT_SEVERITY_HIGH,
                        "entities": [eid],
                        "message": f"EMERGENCY declared for Aircraft {eid}. Simulating emergency dispatch.",
                        "timestamp": time.time()
                    })
            else:
                self.alerted_entities.discard(eid)
                
        for eid, v in gnd_snap.items():
             if v.get("emergency_flag"):
                 if eid not in self.alerted_entities:
                     self.alerted_entities.add(eid)
                     alerts.append({
                        "alert_type": "EMERGENCY_DECLARED",
                        "severity": config.CONFLICT_SEVERITY_HIGH,
                        "entities": [eid],
                        "message": f"EMERGENCY declared for Vehicle {eid}. Simulating emergency dispatch.",
                        "timestamp": time.time()
                    })
             else:
                 self.alerted_entities.discard(eid)
                 
        return alerts
