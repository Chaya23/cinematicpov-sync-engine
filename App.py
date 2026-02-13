import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v16.4", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Please check your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize Session State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. THE DYNAMIC RESOLVER (404 FIX) ---

def get_flash_model():
    """Finds the correct Flash model ID to prevent 404 errors."""
    try:
        for m in genai.list_models():
            if 'gemini-1.5-flash' in m.name and 'generateContent' in m.supported_generation_methods:
                return m.name
        return "models/gemini-1.5-flash" # Hardcoded fallback
    except:
        return "models/gemini-1.5-flash"

# --- 3. UTILITIES ---

def extract_audio(video_path, tmp_dir):
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    # Converts any format to MP3 16k mono for Whisper optimization
    command = f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y"
    subprocess.run(command, shell=True, check=True, capture_output=True)
    return audio_path

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
        try:
            ydl.download([url])
        except Exception as e:
            st.error(f"Download blocked: {e}")
            return None
    
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"):
            return os.path.join(tmp_dir, f)
    return None

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎭 Cast & Crew")
    st.session_state.custom_chars = st.text_area("Edit Names:", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    st.divider()
    st.header("✍️ Author Config")
    pov_char = st.selectbox("Select POV:", char_list)
    style = st.selectbox("Style:", ["Young Adult Novel", "Middle Grade Fantasy", "Gothic Romance"])
    
    st.info("Fusion v16.4: Resolve 404 + Whisper v3")

# --- 5. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Fusion v16.4")
url_input = st.text_input("Episode URL (YouTube/Disney/Solar):")
uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'webm', 'mkv'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Get Video
            video_path = ""
            if uploaded:
                video_path = os.path.join(tmp_dir, uploaded.name)
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("🕵️ Attempting Stealth Download...")
                video_path = download_video(url_input, tmp_dir)

            if not video_path:
                st.error("Could not retrieve video.")
                st.stop()

            # --- STAGE 1: WHISPER ---
            st.info("👂 Whisper: Transcribing verbatim...")
            audio_path = extract_audio(video_path, tmp_dir)
            with open(audio_path, "rb") as f_audio:
                raw_whisper = client_oa.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, response_format="text"
                )
            
            # --- STAGE 2: GEMINI VISION ---
            st.info("☁️ Gemini: Analyzing visuals...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)

            # --- STAGE 3: FUSION ---
            st.info(f"✍️ Authoring {pov_char}'s Chapter...")
            
            # Use Resolver to get the correct model name
            working_model_name = get_flash_model()
            model = genai.GenerativeModel(working_model_name)
            
            fusion_prompt = f"""
            You are a Master Director and YA Novelist.
            CAST: {st.session_state.custom_chars}
            WHISPER TRANSCRIPT: {raw_whisper}
            
            TASK: 
            1. Correct the script by watching the video to match voices to names.
            2. Write a detailed YA novel chapter from {pov_char}'s POV. 
            3. Use the exact dialogue from the Whisper transcript.
            
            FORMAT:
            ---SCRIPT_START---
            [Dialogue]
            ---NOVEL_START---
            [Full Chapter]
            """
            
            response = model.generate_content([video_file, fusion_prompt])
            
            # Parsing logic
            if "---NOVEL_START---" in response.text:
                parts = response.text.split("---NOVEL_START---")
                st.session_state.transcript = parts[0].replace("---SCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Fusion Complete!")
            else:
                st.session_state.transcript = response.text
                st.warning("Could not split sections—outputting raw text.")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 6. OUTPUT ---
if st.session_state.transcript:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Verbatim Script")
        st.text_area("Source", st.session_state.transcript, height=600)
    with r:
        st.subheader(f"📖 {pov_char}'s Chapter")
        st.text_area("Manuscript", st.session_state.novel, height=600)
        st.download_button("💾 Download Chapter (.txt)", st.session_state.novel, file_name=f"{pov_char}_Chapter.txt")
