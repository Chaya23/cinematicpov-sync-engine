import streamlit as st
import os
import tempfile
import json
from pathlib import Path
import time

# 1. Page Config
st.set_page_config(
    page_title="CinematicPOV Sync Engine",
    page_icon="🎬",
    layout="wide"
)

# 2. Simplified Password Check
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    password = st.text_input("Enter Password", type="password")
    if password == "cinematicpov2024":
        st.session_state["password_correct"] = True
        st.rerun()
    else:
        st.stop()

# 3. Imports with error handling
try:
    import yt_dlp
    import openai
    import google.generativeai as genai
    from pydub import AudioSegment
except ImportError as e:
    st.error(f"Missing library: {e}. Check requirements.txt")
    st.stop()

# 4. API Configuration
openai_key = st.secrets.get("OPENAI_API_KEY")
google_key = st.secrets.get("GOOGLE_API_KEY")

if not openai_key or not google_key:
    st.error("Missing API Keys in Streamlit Secrets!")
    st.stop()

openai.api_key = openai_key
genai.configure(api_key=google_key)

# 5. Helper Functions
def download_audio(url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return f"{output_path}.mp3"

# 6. Main App UI
st.title("🎬 CinematicPOV Sync Engine v6.0")

tab1, tab2 = st.tabs(["📥 Process", "📖 Results"])

with tab1:
    url_input = st.text_input("Streaming URL (SolarMovie/YouTube):")
    uploaded_file = st.file_uploader("Or Upload File", type=['mp3', 'mp4', 'wav'])
    pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])
    
    if st.button("START SYNC", type="primary"):
        with st.spinner("Processing..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Get Audio
                if uploaded_file:
                    audio_path = os.path.join(temp_dir, "input.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                else:
                    audio_path = download_audio(url_input, os.path.join(temp_dir, "audio"))
                
                # Step 2: Verbatim Whisper Transcription
                st.text("🎤 Transcribing (Whisper)...")
                with open(audio_path, "rb") as f:
                    transcript = openai.Audio.transcribe("whisper-1", f)
                raw_text = transcript["text"]
                
                # Step 3: Gemini Mapping & Prose
                st.text("🧠 Character Mapping (Gemini)...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(f"Map these speakers: {raw_text}")
                
                st.session_state.transcript = raw_text
                st.session_state.pov_prose = response.text
                st.success("Complete!")

with tab2:
    if "pov_prose" in st.session_state:
        st.markdown(f"### {pov_char}'s POV Narrative")
        st.write(st.session_state.pov_prose)
                        
