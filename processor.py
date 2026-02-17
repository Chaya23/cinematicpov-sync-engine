import os
import subprocess
from dataclasses import dataclass
from dotenv import load_dotenv

import whisper

# --- Optional: pyannote (can fail on Streamlit Cloud) ---
try:
    from pyannote.audio import Pipeline
except Exception:
    Pipeline = None

# --- Optional: Gemini (can fail if package/model mismatch) ---
try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()


@dataclass
class CastScriptResult:
    transcript_text: str
    diarization: object  # Annotation | None
    diarization_error: str | None = None


class CastScriptEngine:
    """
    - Extract mono 16kHz WAV via ffmpeg
    - Transcribe with Whisper (local)
    - Optional diarization with pyannote (HF gated)
    - Optional POV rewrite with Gemini (text-only)
    """

    def __init__(self, whisper_model: str = "base", enable_diarization: bool = False):
        # ---- Whisper ----
        self.stt_model = whisper.load_model(whisper_model)

        # ---- Gemini (optional) ----
        self.llm = None
        gemini_key = os.getenv("GEMINI_API_KEY")
        if genai is not None and gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # Use a safer default model name; you can change later in app UI
                self.llm = genai.GenerativeModel("gemini-1.5-flash")
            except Exception:
                self.llm = None

        # ---- Diarization (optional) ----
        self.diarization_pipeline = None
        self.diarization_error = None

        if enable_diarization:
            if Pipeline is None:
                self.diarization_error = "pyannote.audio not available in this environment."
            else:
                hf_token = os.getenv("HF_TOKEN")
                if not hf_token:
                    self.diarization_error = "HF_TOKEN missing in .env/secrets."
                else:
                    # IMPORTANT: pyannote 3.x prefers token=...
                    try:
                        # community-1 is often easier than 3.1 gating wise
                        model_id = os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-community-1")
                        self.diarization_pipeline = Pipeline.from_pretrained(
                            model_id,
                            token=hf_token
                        )
                    except Exception as e:
                        self.diarization_pipeline = None
                        self.diarization_error = f"Failed to load pyannote pipeline: {e}"

    def extract_audio(self, input_path: str, audio_path: str = "temp_audio.wav") -> None:
        # ffmpeg must be installed (on Streamlit Cloud: packages.txt must include ffmpeg)
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-vn",
            audio_path,
            "-y",
        ]
        subprocess.run(cmd, check=True)

    def process_video_or_url(self, input_path: str) -> CastScriptResult:
        audio_path = "temp_audio.wav"
        self.extract_audio(input_path, audio_path=audio_path)

        diarization = None
        diarization_error = None

        if self.diarization_pipeline is not None:
            try:
                diarization = self.diarization_pipeline(audio_path)
            except Exception as e:
                diarization_error = f"Diarization failed: {e}"
        else:
            diarization_error = self.diarization_error

        result = self.stt_model.transcribe(audio_path)
        transcript = (result.get("text") or "").strip()

        return CastScriptResult(
            transcript_text=transcript,
            diarization=diarization,
            diarization_error=diarization_error
        )

    def rewrite_pov(self, transcript: str, character_name: str, cast_info: str) -> str:
        if not self.llm:
            return (
                "POV rewrite is disabled. Set GEMINI_API_KEY and ensure google-generativeai is installed. "
                "Also confirm the model name is available."
            )

        prompt = f"""ACT AS: A master screenwriter.
STYLE: Modern YA-friendly prose, clean and vivid.
RULES:
- Rewrite strictly from the POV of {character_name}.
- Keep events faithful to the transcript (no new plot points).
- Add internal thoughts, biases, and emotions of {character_name}.
- Don't invent speaker names that aren't in CAST INFO.

CAST INFO:
{cast_info}

TRANSCRIPT:
{transcript}
""".strip()

        resp = self.llm.generate_content(prompt)
        return getattr(resp, "text", "").strip()
