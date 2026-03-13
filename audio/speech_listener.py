import sounddevice as sd
import numpy as np
import threading
import queue
import time
import wave
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class SpeechListener:
    def __init__(self, callback: Callable[[np.ndarray], None], chunk_duration_sec: int = 5):
        self.callback = callback
        self.chunk_duration_sec = chunk_duration_sec
        self.rate = 16000
        self.channels = 1
        
        self.is_listening = False
        self._record_thread = None
        self._worker_thread = None
        self.audio_queue = queue.Queue()
        
    def start_microphone(self):
        if self.is_listening:
            return
        self.is_listening = True
        
        # Start queue processor
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        
        # Start recording
        self._record_thread = threading.Thread(target=self._record, daemon=True)
        self._record_thread.start()
        
        logger.info("Started microphone listener using thread-safe queue.")
        
    def stop(self):
        self.is_listening = False
        
        # Unblock queue
        self.audio_queue.put(None)
        
        if self._record_thread:
            self._record_thread.join(timeout=2)
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
            
        logger.info("Stopped microphone listener.")
        
    def _process_queue(self):
        while self.is_listening:
            try:
                 # Block until an item is available
                 data = self.audio_queue.get(timeout=1.0)
                 if data is None: # Sentinel for shutdown
                     break
                 
                 # Sequentially process via callback (STT -> LLM) ensures thread safety
                 self.callback(data)
                 self.audio_queue.task_done()
            except queue.Empty:
                 continue
            except Exception as e:
                 logger.error(f"Error in audio processing worker: {e}")
            
    def _record(self):
        frames_per_chunk = int(self.rate * self.chunk_duration_sec)
        
        try:
            with sd.InputStream(samplerate=self.rate, channels=self.channels, dtype='float32') as stream:
                while self.is_listening:
                    data, overflowed = stream.read(frames_per_chunk)
                    
                    if overflowed:
                        logger.warning("Audio input overflow detected.")
                        
                    if self.is_listening and len(data) > 0:
                        np_data = data.flatten()
                        # Feed the pipeline safely
                        self.audio_queue.put(np_data)
                        
        except Exception as e:
            logger.error(f"Failed to open microphone: {e}. Ensure plugins granted permission.")
            self.is_listening = False

    def process_wav_file(self, file_path: str):
        """Simulate real-time streaming from a .wav file using the same pipeline architecture."""
        if not file_path.endswith('.wav'):
             logger.error("Only .wav files are supported for demo mode.")
             return
             
        # Setup worker for queue
        self.is_listening = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
             
        try:
            wf = wave.open(file_path, 'rb')
            if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                 logger.warning(f"WAV file {file_path} should ideally be 16kHz mono. Got {wf.getnchannels()} channels, {wf.getframerate()}Hz.")
                 
            chunk_frames = self.rate * self.chunk_duration_sec
            while self.is_listening:
                data = wf.readframes(chunk_frames)
                if not data:
                    break
                
                np_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                self.audio_queue.put(np_data)
                time.sleep(self.chunk_duration_sec)
                
            wf.close()
        except Exception as e:
            logger.error(f"Failed to process wav file {file_path}: {e}")
        finally:
            self.stop()
