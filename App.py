        import streamlit as st
import os
import tempfile
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

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
client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 2. ROBUST TRANSCRIPTION (5-min chunks to stay under 25MB) ---
def transcribe_robust(file_path):
    audio = AudioSegment.from_file(file_path)
    five_minutes = 5 * 60 * 1000 
    chunks = range(0, len(audio), five_minutes)
    
    full_transcript = ""
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, start_time in enumerate(chunks):
        status_text.text(f"Processing part {i+1} of {len(chunks)}...")
        chunk = audio[start_time:start_time + five_minutes]
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_chunk:
            chunk.export(tmp_chunk.name, format="mp3", bitrate="64k")
            with open(tmp_chunk.name, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f
                )
                full_transcript += response.text + " "
            os.unlink(tmp_chunk.name)
        progress_bar.progress((i + 1) / len(chunks))
    
    status_text.text("Transcription complete!")
    return full_transcript

# --- 3. NUCLEAR BYPASS DOWNLOADER ---
def download_audio_safe(url, output_dir):
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web_creator'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        'user_agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.join(output_dir, "audio.mp3")
    except: return None

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v8.0")

url_input = st.text_input("Paste Link:")
uploaded_file = st.file_uploader("OR Upload Audio File Directly:", type=['mp3', 'mp4', 'm4a'])
pov_char = st.selectbox("POV Character", ["Justin", "Billie", "Roman", "Winter"])

if st.button("START SYNC", type="primary"):
    with st.spinner("Processing..."):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = None
            if uploaded_file:
                audio_path = os.path.join(temp_dir, "input.mp3")
                with open(audio_path, "wb") as f: f.write(uploaded_file.getbuffer())
            elif url_input:
                audio_path = download_audio_safe(url_input, temp_dir)
            
            if audio_path and os.path.exists(audio_path):
                # 1. Transcribe
                raw_text = transcribe_robust(audio_path)
                
                # 2. Map to Character using the NEW 2026 Model
                st.text(f"🧠 Mapping {pov_char} (Using Gemini 2.5 Flash)...")
                
                # We use the updated 2026 model name here
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"Write a 1st person POV narrative for {pov_char} from 'Wizards Beyond Waverly Place' based on this script: {raw_text}"
                
                try:
                    res = model.generate_content(prompt)
                    st.markdown(f"## {pov_char}'s Story")
                    st.write(res.text)
                    st.session_state.pov_prose = res.text
                except Exception as e:
                    st.error(f"Gemini Error: {e}")
            else:
                st.error("Failed to extract audio. Site may be blocked.")
