import streamlit as st
import os
import tempfile
from pathlib import Path
from openai import OpenAI  # NEW: OpenAI V1 client
import google.generativeai as genai
import yt_dlp

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="CinematicPOV Sync Engine", page_icon="🎬", layout="wide")

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    pwd = st.text_input("Enter Password", type="password")
    if pwd == "cinematicpov2024":
        st.session_state["password_correct"] = True
        st.rerun()
    st.stop()

# --- 2. API CONFIG ---
openai_key = st.secrets.get("OPENAI_API_KEY")
google_key = st.secrets.get("GOOGLE_API_KEY")

if not openai_key or not google_key:
    st.error("Missing API Keys! Add them to Streamlit Secrets.")
    st.stop()

# NEW: Initialize OpenAI Client for 2026 standard
client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 3. BYPASS DOWNLOADER ---
def download_audio_safe(url, output_dir):
    """Downloads audio with mobile headers to bypass streaming blocks."""
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        # Tricking the site into thinking we are an iPhone browser
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'referer': 'https://solarmovies.win/',
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.join(output_dir, "audio.mp3")
    except Exception as e:
        st.error(f"Download Blocked: Try uploading the file manually from your phone!")
        return None

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v6.0")

tab1, tab2 = st.tabs(["📥 Process", "📖 Results"])

with tab1:
    url_input = st.text_input("Paste Link (SolarMovie/YouTube):")
    uploaded_file = st.file_uploader("OR Upload File", type=['mp3', 'mp4', 'm4a'])
    pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])
    
    if st.button("START SYNC", type="primary"):
        if not url_input and not uploaded_file:
            st.warning("Please provide a link or a file first!")
            st.stop()
            
        with st.spinner("Processing..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_path = None
                
                # Step 1: Get Audio
                if uploaded_file:
                    audio_path = os.path.join(temp_dir, "input.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                elif url_input:
                    audio_path = download_audio_safe(url_input, temp_dir)
                
                if audio_path and os.path.exists(audio_path):
                    # Step 2: NEW 2026 Whisper Method
                    st.text("🎤 Transcribing (Whisper v1)...")
                    with open(audio_path, "rb") as f:
                        # Fixed the APIRemovedInV1 error here
                        response = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=f
                        )
                    raw_text = response.text 
                    
                    # Step 3: Gemini Mapping & Prose
                    st.text("🧠 Character Mapping (Gemini)...")
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Using this transcript, write a detailed first-person POV narrative from {pov_char}'s perspective: {raw_text}"
                    response = model.generate_content(prompt)
                    
                    st.session_state.pov_prose = response.text
                    st.success("Complete! View the Results tab.")
                else:
                    st.error("Audio processing failed.")

with tab2:
    if "pov_prose" in st.session_state:
        st.write(st.session_state.pov_prose)
                        
