import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Sync v9.7", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. TRANSCRIPTION (Chunking for 413 fix) ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_ms = 5 * 60 * 1000 
    full_text = ""
    for start in range(0, len(audio), chunk_ms):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio[start:start+chunk_ms].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
    return full_text

# --- 3. STEALTH DOWNLOADER (The Fix) ---
def download_stealth(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "audio.%(ext)s")
    
    # Check if user uploaded a cookies file to GitHub
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'cookiefile': cookie_path, # THIS IS THE KEY FOR DISNEY/SOLAR
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

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v9.7")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Paste Link (YouTube/DisneyNow/Solar):")
    uploaded = st.file_uploader("OR Upload Audio File Directly", type=['mp3', 'mp4', 'm4a'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("POV Character:", chars + ["Custom..."])
    if pov_char == "Custom...": pov_char = st.text_input("Enter Name:")

if st.button("🔥 START SYNC", type="primary"):
    with st.spinner("Bypassing security and extracting..."):
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # Step 1: Download/Load
                path = download_stealth(url_input, tmp_dir) if not uploaded else os.path.join(tmp_dir, "in.mp3")
                if uploaded:
                    with open(path, "wb") as f: f.write(uploaded.getbuffer())

                # Step 2: Transcribe
                st.text("🎤 Transcribing...")
                transcript = get_transcript(path)
                
                # Step 3: Grounding & Novel
                st.text("🧠 Grounding with Wiki & Writing Story...")
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"""
                You are a 'Wizards Beyond Waverly Place' expert. 
                TRANSCRIPT: {transcript[:3000]}
                
                TASK:
                1. Identify the characters correctly. 
                   - MILO wants the monkey. 
                   - BILLIE gets the makeover. 
                   - ROMAN & WINTER do the 'back together' spell.
                2. Generate a labeled transcript (Name: Dialogue).
                3. Write a first-person POV novel chapter for {pov_char}.
                
                FORMAT:
                ---TRANSCRIPT---
                [Labeled Text]
                ---POV---
                [Novel Content]
                """
                
                res = model.generate_content(prompt)
                parts = res.text.split("---POV---")
                
                st.session_state.labeled = parts[0].replace("---TRANSCRIPT---", "")
                st.session_state.novel = parts[1]
                st.success("Sync Complete!")

            except Exception as e:
                st.error(f"DOWNLOAD ERROR: Disney/Solar is blocking this server IP. \n\nFIX: Download the audio to your phone/PC first, then use the 'Upload Audio File' box above.")

# --- 5. RESULTS ---
t1, t2 = st.tabs(["📖 Character POV", "📝 Labeled Transcript"])
if "novel" in st.session_state:
    with t1:
        st.write(st.session_state.novel)
        st.download_button("Download Chapter", st.session_state.novel, "POV_Chapter.txt")
    with t2:
        st.text_area("Copy Labeled Transcript:", st.session_state.labeled, height=400)
