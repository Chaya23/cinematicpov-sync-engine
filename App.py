    import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Sync v10.7", layout="wide")

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    proxy_url = st.secrets.get("PROXY_URL") 
except Exception as e:
    st.error("Missing API Keys in Secrets.")
    st.stop()

# --- 2. TRANSCRIPTION ENGINE ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_ms = 5 * 60 * 1000 
    full_text = ""
    progress_bar = st.progress(0)
    chunks = list(range(0, len(audio), chunk_ms))
    
    for i, start in enumerate(chunks):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio[start:start+chunk_ms].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
            progress_bar.progress((i + 1) / len(chunks))
    return full_text

# --- 3. DOWNLOADER ---
def download_audio(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "audio.%(ext)s")
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'quiet': True,
        'proxy': proxy_url,
        'geo_bypass': True,
        'cookiefile': cookie_path,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36'},
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "audio.mp3")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v10.7")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Link (YouTube/Disney/Solar):")
    uploaded = st.file_uploader("OR Upload File:", type=['mp3', 'mp4', 'm4a'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select Character POV:", chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Name:")

if st.button("🔥 START SYNC", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            if uploaded:
                path = os.path.join(tmp_dir, "in.mp3")
                with open(path, "wb") as f: f.write(uploaded.getbuffer())
            elif url_input:
                path = download_audio(url_input, tmp_dir)
            else:
                st.error("No source provided!")
                st.stop()

            st.info("🎤 Transcribing full episode...")
            raw_text = get_transcript(path)
            
            st.info("🧠 Syncing with 2026 Gemini Engine...")
            
            # --- UPDATED MODEL SELECTION ---
            # Trying 2.0-flash which is the current 2026 workhorse
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
            except:
                model = genai.GenerativeModel('gemini-pro') # Fallback
            
            prompt = f"""
            Identify characters in this transcript: {raw_text}
            Grounding facts: Roman made the Lacey vase, Billie got the Staten Island makeover, Milo wants the monkey.
            1. Provide a FULL Labeled Transcript (Name: Dialogue).
            2. Write a 1st-person POV chapter for {pov_char}.
            
            FORMAT:
            ---TRANSCRIPT---
            [Labeled Text]
            ---POV---
            [Novel Chapter]
            """
            
            res = model.generate_content(prompt)
            parts = res.text.split("---POV---")
            
            st.session_state.labeled = parts[0].replace("---TRANSCRIPT---", "")
            st.session_state.story = parts[1]
            st.success("Sync Complete!")

        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. TABS ---
t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])
if "story" in st.session_state:
    with t1:
        st.write(st.session_state.story)
        st.download_button("Download Story", st.session_state.story, "story.txt")
    with t2:
        st.text_area("Full Transcript:", st.session_state.labeled, height=500)
