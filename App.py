import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v16.3", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Check your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize Session State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. THE STEALTH DOWNLOADER ---

def extract_audio(video_path, tmp_dir):
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    # Convert any format (mp4/webm) to mp3 for Whisper
    command = f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y"
    subprocess.run(command, shell=True, check=True, capture_output=True)
    return audio_path

def download_video(url, tmp_dir):
    """Uses advanced headers to avoid the 'Sign in to confirm you are not a bot' error."""
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
        try:
            ydl.download([url])
        except Exception as e:
            st.error(f"Download blocked by site: {e}")
            return None
    
    # Scans for the file (could be .mp4, .webm, or .mkv)
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"):
            return os.path.join(tmp_dir, f)
    return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🎭 Cast & Crew")
    st.session_state.custom_chars = st.text_area("Edit Names:", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    st.divider()
    st.header("✍️ Author Config")
    pov_char = st.selectbox("Select POV:", char_list)
    style = st.selectbox("Style:", ["Young Adult Novel", "Middle Grade Fantasy", "Gothic Romance"])
    
    st.info("Engine: OpenAI Whisper + Gemini 1.5 Flash")

# --- 4. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Fusion v16.3")
url_input = st.text_input("Episode URL (YouTube/Solar/Direct):")
uploaded = st.file_uploader("OR Upload Video (Recommended for bypass):", type=['mp4', 'webm', 'mkv'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            video_path = ""
            if uploaded:
                video_path = os.path.join(tmp_dir, uploaded.name)
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("🕵️ Attempting Stealth Download...")
                video_path = download_video(url_input, tmp_dir)

            if not video_path:
                st.error("Could not retrieve video. Please download the file to your device and use the 'Upload' button.")
                st.stop()

            # --- PROCESS STAGE 1: WHISPER ---
            st.info("👂 Whisper is listening (Verbatim)...")
            audio_path = extract_audio(video_path, tmp_dir)
            with open(audio_path, "rb") as f_audio:
                raw_whisper = client_oa.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, response_format="text"
                )
            
            # --- PROCESS STAGE 2: GEMINI ---
            st.info("☁️ Gemini is watching (Vision)...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)

            # --- PROCESS STAGE 3: FUSION ---
            st.info(f"✍️ Authoring {pov_char}'s Chapter...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            fusion_prompt = f"""
            You are a Master Director and YA Novelist.
            CAST: {st.session_state.custom_chars}
            WHISPER TRANSCRIPT: {raw_whisper}
            
            TASK 1: Match names to the dialogue in the transcript by watching the video.
            TASK 2: Write a detailed YA novel chapter from {pov_char}'s POV. 
            Include deep internal thoughts, descriptions of the Staten Island makeover, and the 'fused' feeling.
            
            FORMAT:
            ---SCRIPT_START---
            [Dialogue]
            ---NOVEL_START---
            [Full Chapter]
            """
            
            response = model.generate_content([video_file, fusion_prompt])
            
            if "---NOVEL_START---" in response.text:
                parts = response.text.split("---NOVEL_START---")
                st.session_state.transcript = parts[0].replace("---SCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Fusion Complete!")
            else:
                st.session_state.transcript = response.text
                st.warning("AI combined the output—displaying raw text.")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. THE STUDIO OUTPUT ---
if st.session_state.transcript:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Verbatim Script")
        st.text_area("Source", st.session_state.transcript, height=600)
    with r:
        st.subheader(f"📖 {pov_char}'s Chapter")
        st.text_area("Manuscript", st.session_state.novel, height=600)
        # Mobile Download/Save Button
        st.download_button(
            label="💾 Download Chapter (.txt)", 
            data=st.session_state.novel, 
            file_name=f"{pov_char}_Chapter.txt",
            mime="text/plain"
        )
