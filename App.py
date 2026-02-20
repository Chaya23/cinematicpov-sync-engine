import streamlit as st
from google import genai
from google.genai import types
import whisper
import subprocess
import os
import time
import re
from datetime import datetime
from docx import Document
from io import BytesIO
import shutil

# ==================== 2026 CONFIGURATION ====================
# Latest Gemini 3.1 Pro released February 19, 2026
MODEL_ID = "gemini-3.1-pro-preview" 

# Initialize 2026 SDK Client with v1beta for Preview features
client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"],
    http_options={'api_version': 'v1beta'}
)

@st.cache_resource
def load_whisper():
    # 'turbo' is the 2026 standard: high accuracy + 50% less RAM
    return whisper.load_model("turbo")

whisper_engine = load_whisper()

# ==================== PRODUCTION ENGINE ====================
def run_production(video_path, item):
    with st.status("🧠 Deep Processing (Gemini 3.1 Pro + Whisper Turbo)...", expanded=True) as status:
        
        # 1. VERBATIM TRANSCRIPTION (The Ear)
        status.write("🎙️ Whisper Turbo: Capturing verbatim stutters...")
        audio_path = f"{video_path}.mp3"
        subprocess.run(["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"], check=True)
        w_res = whisper_engine.transcribe(audio_path, beam_size=5)
        verbatim_transcript = w_res['text']
        
        # 2. VIDEO UPLOAD (The Eye)
        status.write("👁️ Gemini 3.1 Pro: Scanning 0.6GB+ Video...")
        video_ref = client.files.upload(
            file=video_path,
            config=types.UploadFileConfig(mime_type="video/mp4")
        )
        while video_ref.state == "PROCESSING":
            time.sleep(5) # Faster polling for 2026 API
            video_ref = client.files.get(name=video_ref.name)
        
        # 3. AGENTIC FUSION & GROUNDING
        status.write("✍️ Finalizing 5,000-word POV Production...")
        prompt = f"""
        Role: Senior Script Supervisor & Novelist.
        
        INPUT TRANSCRIPT: {verbatim_transcript}
        POV CHARACTER: {item['pov']}
        CAST INFO: {item['cast']}
        
        TASK:
        1. TAGGED TRANSCRIPT: Assign character names to EVERY line. Match visual cues to audio.
        2. POV NOVEL (5,000+ words): Write {item['pov']}'s First-Person POV chapter.
           Include: Verbatim dialogue, internal sensory thoughts, and show lore.
        """
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[video_ref, prompt],
            config=types.GenerateContentConfig(
                # Use Google Search for Lore/Character verification
                tools=[types.Tool(google_search=types.GoogleSearch())],
                # 2026 'Thinking' config replaces thinking_budget
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                # Set High Resolution for better multi-camera speaker identification
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
                temperature=0.2
            )
        )
        return response.text
