import streamlit as st
import os
import tempfile
import openai
import google.generativeai as genai
from pathlib import Path
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

openai.api_key = openai_key
genai.configure(api_key=google_key)

# --- 3. THE FIX: BYPASS DOWNLOADER ---
def download_audio_safe(url, output_dir):
    """Downloads audio with mobile-mimicking headers to bypass blocks."""
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        # Tricking the site to think we are a real Chrome browser
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
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
        st.error(f"Download Blocked: The website is stopping the AI. Try uploading the file manually!")
        return None

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v6.0")

tab1, tab2 = st.tabs(["📥 Process", "📖 Results"])

with tab1:
    url_input = st.text_input("Paste Streaming Link (SolarMovie/YouTube):")
    uploaded_file = st.file_uploader("OR Upload Audio File Directly (Recommended for Mobile)", type=['mp3', 'mp4', 'm4a'])
    pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])
    
    if st.button("START SYNC", type="primary"):
        with st.spinner("Processing... this takes 1-3 minutes."):
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
                    # Step 2: Whisper (The Ear)
                    with open(audio_path, "rb") as f:
                        transcript = openai.Audio.transcribe("whisper-1", f)
                    
                    # Step 3: Gemini (The Storyteller)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Map speakers and write a first-person POV for {pov_char} based on this: {transcript['text']}"
                    response = model.generate_content(prompt)
                    
                    st.session_state.pov_prose = response.text
                    st.success("Sync Complete! Check the Results tab.")
                else:
                    st.warning("No audio found. Try uploading the file instead of using a link.")

with tab2:
    if "pov_prose" in st.session_state:
        st.write(st.session_state.pov_prose)
