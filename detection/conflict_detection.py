import time
from typing import Dict, Any, List
import config

class ConflictDetector:
    def __init__(self, aircraft_engine, ground_engine):
        self.aircraft_engine = aircraft_engine
        self.ground_engine = ground_engine
        self.active_conflicts = set()
        
    def detect_conflicts(self) -> List[Dict[str, Any]]:
        alerts_to_send = []
        current_conflicts = set()
        
        ac_snap = self.aircraft_engine.get_snapshot()
        gnd_snap = self.ground_engine.get_snapshot()
        
        def add_alert(alert_type, severity, entities, message, conflict_id):
            current_conflicts.add(conflict_id)
            if conflict_id not in self.active_conflicts:
                alerts_to_send.append({
                    "alert_type": alert_type,
                    "severity": severity,
                    "entities": entities,
                    "message": message,
                    "timestamp": time.time()
                })

        # 1. Runway Conflict Detection
        runway_occupants = {}
        for eid, ac in ac_snap.items():
            runway = ac.get("runway")
            if runway and ac.get("clearance_state") == "granted":
                runway_occupants.setdefault(runway, []).append(eid)
                
        for eid, v in gnd_snap.items():
            req_runway = v.get("runway_entry_request")
            if req_runway:
                if v.get("clearance_state") != "granted":
                    conflict_id = f"RUNWAY_INCURSION_{req_runway}_{eid}"
                    add_alert("RUNWAY_INCURSION_UNAUTHORIZED", config.CONFLICT_SEVERITY_HIGH, [eid],
                              f"Vehicle {eid} is on/requesting runway {req_runway} without clearance.", conflict_id)
                else:
                    runway_occupants.setdefault(req_runway, []).append(eid)
                    
        for rw, occupants in runway_occupants.items():
            if len(occupants) > 1:
                occupants.sort()
                conflict_id = f"RUNWAY_CONFLICT_{rw}_{'-'.join(occupants)}"
                add_alert("RUNWAY_CONFLICT", config.CONFLICT_SEVERITY_HIGH, occupants,
                          f"Runway {rw} occupied/cleared for multiple entities: {', '.join(occupants)}", conflict_id)
                
        # 2. Taxiway Conflict
        taxiway_occupants = {}
        for eid, ac in ac_snap.items():
            route = ac.get("route", [])
            if route and len(route) > 0:
                tw = route[-1]
                taxiway_occupants.setdefault(tw, []).append(eid)
                
        for eid, v in gnd_snap.items():
            pos = v.get("position")
            if pos and pos != "unknown":
                taxiway_occupants.setdefault(pos, []).append(eid)
                
        for tw, occupants in taxiway_occupants.items():
            if len(occupants) > 1:
                occupants.sort()
                conflict_id = f"TAXIWAY_CONFLICT_{tw}_{'-'.join(occupants)}"
                add_alert("TAXIWAY_CONFLICT", config.CONFLICT_SEVERITY_MEDIUM, occupants,
                          f"Taxiway segment {tw} occupied by multiple entities: {', '.join(occupants)}", conflict_id)
                 
        # 3. Clearance Violation
        for eid, ac in ac_snap.items():
            if ac.get("phase") in ["taxi", "takeoff", "landing"] and ac.get("clearance_state") == "pending":
                conflict_id = f"CLEARANCE_VIOLATION_AC_{eid}"
                add_alert("CLEARANCE_VIOLATION", config.CONFLICT_SEVERITY_MEDIUM, [eid],
                          f"Aircraft {eid} intent {ac['phase']} detected without clearance.", conflict_id)
                
        for eid, v in gnd_snap.items():
             if len(v.get("route", [])) > 0 and v.get("clearance_state") == "pending":
                 conflict_id = f"CLEARANCE_VIOLATION_VEH_{eid}"
                 add_alert("CLEARANCE_VIOLATION", config.CONFLICT_SEVERITY_MEDIUM, [eid],
                           f"Vehicle {eid} movement detected without clearance.", conflict_id)
                 
        # Update active conflicts state to ONLY the current ones
        self.active_conflicts = current_conflicts
                 
        return alerts_to_send
