import logging
from faster_whisper import WhisperModel
import config

logger = logging.getLogger(__name__)

class STTEngine:
    def __init__(self, model_size=config.WHISPER_MODEL_SIZE):
        logger.info(f"Loading Whisper model '{model_size}' on CPU...")
        try:
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Faster-Whisper model: {e}")
            self.model = None
        
    def transcribe(self, audio_data) -> str:
        """
        Transcribe audio array (numpy) to text.
        """
        if not self.model:
            return ""
            
        try:
            # Provide ATC context to bias the STT engine away from general conversational words
            prompt = "ATC communications. MAYDAY, PAN-PAN, runway, taxiway, clearance, Changi, tower, ground, hold short."
            segments, info = self.model.transcribe(
                audio_data, 
                beam_size=5, 
                vad_filter=config.VAD_FILTER,
                initial_prompt=prompt
            )
            text = " ".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            logger.error(f"STT Error during transcription: {e}")
            return ""
