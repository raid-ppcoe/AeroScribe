import json
import logging
from typing import Dict, Any
import config
import queue
import threading

logger = logging.getLogger(__name__)

class EventStore:
    def __init__(self):
        self.events_file = config.EVENTS_LOG_PATH
        self.alerts_file = config.ALERTS_LOG_PATH
        self.log_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        
    def _process_queue(self):
        while True:
            try:
                task = self.log_queue.get()
                if task is None:
                    break
                filepath, data = task
                self._append_to_file(filepath, data)
                self.log_queue.task_done()
            except Exception as e:
                logger.error(f"Error in EventStore queue processor: {e}")

    def _append_to_file(self, filepath: str, data: Dict[str, Any]):
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to {filepath}: {e}")
            
    def stop(self):
        self.log_queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
            
    def log_event(self, parsed_event: Dict[str, Any], raw_transcript: str = "", state_snapshot: Dict[str, Any] = None):
        log_entry = {
            "timestamp": parsed_event.get("timestamp"),
            "raw_transcript": raw_transcript,
            "parsed_event": parsed_event,
            "state_snapshot": state_snapshot or {}
        }
        self.log_queue.put((self.events_file, log_entry))
        
    def log_alert(self, alert: Dict[str, Any]):
        self.log_queue.put((self.alerts_file, alert))
