import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v16.5", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize Session State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. THE ULTIMATE 404 FIX: MODEL RESOLVER ---

def resolve_model_id():
    """Fetches the exact string required by the API to avoid 404s."""
    try:
        # Get all models that support content generation
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority 1: Flash 1.5 (Standard for Vision)
        for m in available_models:
            if "gemini-1.5-flash" in m:
                return m
        
        # Priority 2: Any Gemini 1.5 model
        for m in available_models:
            if "1.5" in m:
                return m
                
        return available_models[0]
    except Exception as e:
        return "gemini-1.5-flash" # Absolute fallback

# --- 3. CORE UTILITIES ---

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'quiet': True,
        'headers': {'User-Agent': 'Mozilla/5.0'}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except:
            return None
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"): return os.path.join(tmp_dir, f)
    return None

def extract_audio(video_path, tmp_dir):
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    subprocess.run(f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y", shell=True)
    return audio_path

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎭 Cast")
    st.session_state.custom_chars = st.text_area("Names:", st.session_state.custom_chars)
    pov_char = st.selectbox("POV:", [c.strip() for c in st.session_state.custom_chars.split(",")])
    style = st.selectbox("Style:", ["YA Novel", "Dark Fantasy", "Middle Grade"])
    st.info("Fix: Dynamic Model Discovery")

# --- 5. MAIN UI ---
st.title("🎬 CinematicPOV Fusion v16.5")
url_input = st.text_input("Episode URL:")
uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'webm', 'mkv'])

if st.button("🚀 START FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # 1. Video Acquisition
            video_path = ""
            if uploaded:
                video_path = os.path.join(tmp_dir, uploaded.name)
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("🕵️ Downloading...")
                video_path = download_video(url_input, tmp_dir)

            if not video_path:
                st.error("Video retrieval failed.")
                st.stop()

            # 2. Whisper (Audio)
            st.info("👂 Transcribing Audio...")
            audio_path = extract_audio(video_path, tmp_dir)
            with open(audio_path, "rb") as f_audio:
                raw_whisper = client_oa.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, response_format="text"
                )

            # 3. Gemini (Vision)
            st.info("☁️ Analyzing Visuals...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            # 4. The Fusion Stage
            st.info(f"✍️ Authoring {pov_char}'s POV...")
            
            # THE FIX: Resolve model name dynamically
            model_id = resolve_model_id()
            model = genai.GenerativeModel(model_id)
            
            prompt = f"""
            You are a Professional YA Author. 
            CAST: {st.session_state.custom_chars}
            TRANSCRIPT: {raw_whisper}
            
            TASK: 
            1. Create a script matching the transcript to the characters on screen.
            2. Write a full chapter from {pov_char}'s POV using the EXACT dialogue.
            
            FORMAT:
            ---SCRIPT---
            [Script]
            ---NOVEL---
            [Chapter]
            """
            
            response = model.generate_content([video_file, prompt])
            
            if "---NOVEL---" in response.text:
                parts = response.text.split("---NOVEL---")
                st.session_state.transcript = parts[0].replace("---SCRIPT---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Success!")
            else:
                st.session_state.transcript = response.text
            
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"API Error: {e}")
            # Diagnostic: List models if error occurs
            st.write("Available models on your key:", [m.name for m in genai.list_models()])

# --- 6. OUTPUT ---
if st.session_state.transcript:
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Script")
        st.text_area("V1", st.session_state.transcript, height=600)
    with r:
        st.subheader("📖 Novel")
        st.text_area("V1", st.session_state.novel, height=600)
