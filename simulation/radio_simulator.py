import time
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

class RadioSimulator:
    def __init__(self, text_callback: Callable[[str], None], mode: str = "normal", delay_between_calls=4.0):
        self.text_callback = text_callback
        self.mode = mode
        self.delay = delay_between_calls
        self.is_running = False
        self._thread = None
        
        self.script_normal = [
            # --- NORMAL OPERATIONS ---
            # Arrival: Recover -> Landing -> Taxi in
            "Changi Tower, Jetstar 112 heavy, ILS approach Runway 02C.",
            "Jetstar 112, Changi Tower, cleared to land Runway 02C. Wind 040 degrees at 12 knots.",
            "Cleared to land Runway 02C, Jetstar 112.",
            "Changi Tower, Jetstar 112, runway vacated via South Cross.",
            "Jetstar 112, welcome to Changi. Contact Ground.",
            "Changi Ground, Jetstar 112, clear of Runway 02C, request taxi.",
            "Jetstar 112, Changi Ground, taxi to Terminal 1 via South Cross and Bravo.",
            "Taxi to Terminal 1 via South Cross and Bravo, Jetstar 112.",
            "Ground, Jetstar 112 approaching Terminal 1.",
            "Jetstar 112, roger, dock at Gate clear.",
            
            # Departure: Taxi out -> Taxi to Runway -> Depart
            "Changi Ground, Singapore 318 at Terminal 2, request pushback.",
            "Singapore 318, Changi Ground, pushback and start approved.",
            "Ground, Singapore 318 ready to taxi.",
            "Singapore 318, taxi to holding point Runway 02L via Alpha and North Cross.",
            "Taxi to holding point Runway 02L via Alpha and North Cross, Singapore 318.",
            "Singapore 318, contact Changi Tower.",
            "Changi Tower, Singapore 318 holding short Runway 02L.",
            "Singapore 318, Changi Tower, line up and wait Runway 02L.",
            "Line up and wait Runway 02L, Singapore 318.",
            "Singapore 318, wind 050 degrees 14 knots, Runway 02L, cleared for takeoff.",
            "Cleared for takeoff Runway 02L, Singapore 318.",
            "Singapore 318, airborne, contact Departure. Good day."
        ]
        
        self.script_emergency = [
            # --- EMERGENCY OPERATIONS ---
            # Departure: Taxi out -> Taxi to Runway -> Emerg
            "Changi Ground, Cargo 99 heavy at Cargo, request pushback.",
            "Cargo 99, Changi Ground, pushback approved.",
            "Ground, Cargo 99 ready to taxi.",
            "Cargo 99, taxi to holding point Runway 02C via Whiskey and South Cross.",
            "Taxi to holding point Runway 02C via Whiskey and South Cross, Cargo 99.",
            "Cargo 99, contact Changi Tower.",
            "Changi Tower, Cargo 99 holding short Runway 02C.",
            "Cargo 99, Changi Tower, line up and wait Runway 02C.",
            "Line up and wait Runway 02C, Cargo 99.",
            "Cargo 99, wind 040 degrees 10 knots, Runway 02C, cleared for takeoff.",
            "Cleared for takeoff Runway 02C, Cargo 99.",
            
            # THE EMERGENCY
            "MAYDAY, MAYDAY, MAYDAY, Cargo 99, Engine 2 fire! Rejecting takeoff on Runway 02C. Requesting immediate fire and medical assistance!",
            "Cargo 99, Changi Tower, roger MAYDAY. Emergency response activated. Hold position on Runway 02C.",
            
            # EMERGENCY RESPONSE DISPATCH
            "Ground to Fire Tender 1 and Ambulance 1, proceed immediately to Runway 02C via North Cross. Aircraft Cargo 99 has engine fire.",
            "Fire Tender 1 and Ambulance 1 proceeding to Runway 02C via North Cross.",
            "Ground to Tug 4, proceed to Runway 02C via Victor to stand by for towing.",
            "Tug 4 proceeding to Runway 02C via Victor, standing by for tow.",
            
            # RECOVERY AFTER EMERGENCY
            "Tower, Fire Tender 1, fire extinguished. Passengers secure with Ambulance 1.",
            "Roger Fire Tender 1. Tug 4, you are cleared to tow Cargo 99 off Runway 02C to Changi East.",
            "Tug 4, returning to Changi East via Whiskey and South Cross with Cargo 99 in tow."
        ]
        
    def start(self):
        if self.is_running: return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_sim, daemon=True)
        self._thread.start()
        logger.info(f"Started scripted radio simulator in {self.mode} mode.")
        
    def stop(self):
        self.is_running = False
        if self._thread:
             self._thread.join(timeout=2)
             
    def _run_sim(self):
        # Give UI a moment to connect
        time.sleep(3.0) 
        
        script_to_run = self.script_emergency if self.mode == "emergency" else self.script_normal
        
        while self.is_running:
            for line in script_to_run:
                if not self.is_running: break
                
                logger.info(f"SIMULATOR 📡 : {line}")
                self.text_callback(line)
                
                time.sleep(self.delay)
            
            if self.is_running:
                logger.info("Restarting simulator script loop in 2s...")
                time.sleep(2.0)
                
        logger.info("End of simulator script.")
