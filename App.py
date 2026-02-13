import streamlit as st
import os
import tempfile
from pathlib import Path
from openai import OpenAI
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

# API Keys
openai_key = st.secrets.get("OPENAI_API_KEY")
google_key = st.secrets.get("GOOGLE_API_KEY")

if not openai_key or not google_key:
    st.error("Missing API Keys! Add them to Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 2. THE "NUCLEAR" BYPASS DOWNLOADER ---
def download_audio_safe(url, output_dir):
    """
    Uses aggressive Android spoofing and Geo-Bypass 
    to fight 'Video Not Available' errors.
    """
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        
        # --- GEO-BYPASS ---
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        
        # --- ANDROID API SPOOF (The Fix for 'Not Available') ---
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web_creator'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        
        # --- HEADERS ---
        'user_agent': 'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
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
        st.error(f"❌ Server Blocked: The cloud IP is banned by the site. Error: {e}")
        return None

# --- 3. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v6.0")

tab1, tab2 = st.tabs(["📥 Process", "📖 Results"])

with tab1:
    url_input = st.text_input("Paste Link (YouTube/SolarMovie/DisneyNow):")
    uploaded_file = st.file_uploader("OR Upload Audio File Directly", type=['mp3', 'mp4', 'm4a', 'wav'])
    pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])
    
    if st.button("START SYNC", type="primary"):
        if not url_input and not uploaded_file:
            st.warning("Please provide a link or a file!")
            st.stop()
            
        with st.spinner("Syncing Engine..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_path = None
                
                # Step 1: Get Audio
                if uploaded_file:
                    audio_path = os.path.join(temp_dir, "input.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                elif url_input:
                    audio_path = download_audio_safe(url_input, temp_dir)
                
                # Step 2: Validate and Transcribe
                if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                    st.text("🎤 Transcribing (Whisper v1)...")
                    try:
                        with open(audio_path, "rb") as f:
                            # OpenAI V1 Syntax
                            response = client.audio.transcriptions.create(
                                model="whisper-1", 
                                file=f
                            )
                        raw_text = response.text
                        
                        # Step 3: Gemini POV Narrative
                        st.text(f"🧠 Mapping {pov_char}'s perspective...")
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = (
                            f"Act as a professional scriptwriter. Using the following transcript, "
                            f"write a first-person narrative chapter from the perspective of {pov_char}. "
                            f"Focus on their inner monologue and reactions. \n\nTranscript: {raw_text}"
                        )
                        res = model.generate_content(prompt)
                        st.session_state.pov_prose = res.text
                        st.success("Complete!")
                    except Exception as e:
                        st.error(f"AI Processing Error: {e}")
                else:
                    st.error("Extraction failed. Try uploading the audio file manually.")

with tab2:
    if "pov_prose" in st.session_state:
        st.markdown(f"### {pov_char}'s POV Narrative")
        st.write(st.session_state.pov_prose)
