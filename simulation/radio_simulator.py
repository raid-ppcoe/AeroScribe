import time
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

class RadioSimulator:
    def __init__(self, text_callback: Callable[[str], None], delay_between_calls=4.0):
        self.text_callback = text_callback
        self.delay = delay_between_calls
        self.is_running = False
        self._thread = None
        
        self.script = [
            # --- MORNING DEPARTURE RUSH ---
            "Changi Ground, Singapore 318, aircraft type Boeing 777, stand F42, request pushback and start.",
            "Singapore 318, Changi Ground, pushback and start approved.",
            "Singapore 318, request taxi.",
            "Singapore 318, taxi to holding point Runway 02L via Alpha and Echo.",
            
            # --- ROUTINE GROUND MAINTENANCE ---
            "Ground, Sweeper 1 requesting to proceed via Charlie to Cargo.",
            "Sweeper 1, proceed via Charlie to Cargo, approved.",
            
            # --- TAKEOFF CLEARANCE ---
            "Singapore 318, wind 050 degrees 12 knots, Runway 02L, cleared for takeoff.",
            "Singapore 318, cleared for takeoff Runway 02L.",
            "Singapore 318, airborne.",
            
            # --- MIDDAY ARRIVAL ---
            "Changi Tower, Scoot 421 is inbound for landing Runway 02C.",
            "Scoot 421, Changi Tower, wind 040 degrees 10 knots, Runway 02C, cleared to land.",
            
            # --- ARRIVAL TAXI ---
            "Scoot 421, welcome to Changi, runway vacated.",
            "Scoot 421, taxi to Platform 1 via Delta and Bravo.",
            
            # --- AFTERNOON DEPARTURE ---
            "Changi Ground, Cathay 711, aircraft type Airbus A350, Terminal 2, request pushback.",
            "Cathay 711, Changi Ground, pushback approved.",
            "Cathay 711, request taxi.",
            "Cathay 711, taxi to holding point Runway 02R via Victor.",
            
            # --- CLEARANCE & DEPARTURE ---
            "Cathay 711, wind 060 degrees 8 knots, Runway 02R, cleared for takeoff.",
            "Cathay 711, cleared for takeoff Runway 02R.",
            "Cathay 711, airborne, switching to departure control.",
            
            # --- END OF ROTATION ---
            "Ground, Sweeper 1 secured at Cargo.",
            "Sweeper 1, roger, have a good day."
        ]
        
    def start(self):
        if self.is_running: return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_sim, daemon=True)
        self._thread.start()
        logger.info("Started scripted radio simulator.")
        
    def stop(self):
        self.is_running = False
        if self._thread:
             self._thread.join(timeout=2)
             
    def _run_sim(self):
        # Give UI a moment to connect
        time.sleep(3.0) 
        
        while self.is_running:
            for line in self.script:
                if not self.is_running: break
                
                logger.info(f"SIMULATOR 📡 : {line}")
                self.text_callback(line)
                
                time.sleep(self.delay)
            
            if self.is_running:
                logger.info("Restarting simulator script loop in 2s...")
                time.sleep(2.0)
                
        logger.info("End of simulator script.")
