      import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="CinematicPOV Sync v10.5", layout="wide", page_icon="🎬")

# Load Keys from Secrets
try:
    openai_key = st.secrets["OPENAI_API_KEY"]
    google_key = st.secrets["GOOGLE_API_KEY"]
    proxy_url = st.secrets.get("PROXY_URL") # Add your proxy here in Streamlit Secrets
except KeyError:
    st.error("API Keys missing in Streamlit Secrets!")
    st.stop()

client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 2. TRANSCRIPTION ENGINE (Handles 413 Error & Full Episodes) ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_ms = 5 * 60 * 1000  # 5-minute chunks
    full_text = ""
    
    progress_text = st.empty()
    bar = st.progress(0)
    chunks = range(0, len(audio), chunk_ms)
    
    for i, start in enumerate(chunks):
        progress_text.text(f"🎤 Processing Audio Chunk {i+1} of {len(chunks)}...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            # Bitrate 64k keeps file size tiny for OpenAI's 25MB limit
            audio[start:start+chunk_ms].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
        bar.progress((i + 1) / len(chunks))
    
    progress_text.text("✅ Transcription Complete!")
    return full_text

# --- 3. THE "NUCLEAR" BYPASS DOWNLOADER ---
def download_stealth(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "audio.%(ext)s")
    
    # Check for local cookies file
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'quiet': True,
        'proxy': proxy_url,  # THIS FIXES THE BLOCK
        'geo_bypass': True,
        'cookiefile': cookie_path,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://disneynow.com/',
        },
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "audio.mp3")

# --- 4. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Sync Engine v10.5")
st.info("Bypassing IP blocks and grounding with LaughingPlace recaps.")

col1, col2 = st.columns(2)
with col1:
    url_input = st
    
