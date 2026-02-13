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

# Initialize OpenAI Client (Fixes APIRemovedInV1)
client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 3. BYPASS & GEO-BYPASS DOWNLOADER ---
def download_audio_safe(url, output_dir):
    """Downloads audio with geo-bypass and mobile headers."""
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        
        # --- GEO-BYPASS ---
        'geo_bypass': True,
        'geo_bypass_country': 'US', # Fakes a US location
        
        # --- HEADERS & BYPASS ---
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'referer': 'https://www.google.com/',
        'nocheckcertificate': True,
        
        # --- FFmpeg EXTRACTION ---
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
        st.error(f"Download Failed: The site is blocking the server. Error: {e}")
        return None

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v6.0")

tab1, tab2 = st.tabs(["📥 Process", "📖 Results"])

with tab1:
    url_input = st.text_input("Paste Link (SolarMovie/YouTube/DisneyNow):")
    uploaded_file = st.file_uploader("OR Upload Audio File Directly", type=['mp3', 'mp4', 'm4a'])
    pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])
    
    if st.button("START SYNC", type="primary"):
        if not url_input and not uploaded_file:
            st.warning("Please provide a link or a file!")
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
                    # Step 2: OpenAI V1 Transcription
                    st.text("🎤 Transcribing (Whisper v1)...")
                    with open(audio_path, "rb") as f:
                        # Safety check for empty files (common in blocked links)
                        if os.path.getsize(audio_path) < 1000:
                            st.error("Downloaded file is empty. Geo-bypass failed to get the video stream.")
                            st.stop()
                            
                        response = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=f
                        )
                    raw_text = response.text 
                    
                    # Step 3: Gemini Mapping
                    st.text("🧠 Character Mapping (Gemini)...")
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Write a first-person POV narrative for {pov_char} based on this transcript: {raw_text}"
                    res = model.generate_content(prompt)
                    
                    st.session_state.pov_prose = res.text
                    st.success("Complete!")
                else:
                    st.error("Could not process audio. Try a manual file upload.")

with tab2:
    if "pov_prose" in st.session_state:
        st.markdown(f"### {pov_char}'s POV Narrative")
        st.write(st.session_state.pov_prose)
