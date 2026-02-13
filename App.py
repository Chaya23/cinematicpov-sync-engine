import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v16.2", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Ensure both GOOGLE_API_KEY and OPENAI_API_KEY are in Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. THE BYPASS UTILITIES ---

def extract_audio(video_path, tmp_dir):
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    command = f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y"
    subprocess.run(command, shell=True, check=True, capture_output=True)
    return audio_path

def download_video(url, tmp_dir):
    """Bypass version with user-agent headers to prevent 'Video Unavailable' errors."""
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path, 
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'referer': 'https://www.google.com/',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
        ydl.download([url])
    
    # Locate the downloaded file (handling potential extension changes)
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"):
            return os.path.join(tmp_dir, f)
    return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🎭 Character Manager")
    st.session_state.custom_chars = st.text_area("Edit Cast Names:", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    st.divider()
    st.header("✍️ Author Config")
    pov_char = st.selectbox("POV Character:", char_list)
    style = st.selectbox("Style:", ["Young Adult Novel", "Middle Grade Fantasy", "Gothic Romance"])
    
    st.info("Fusion v16.2: Whisper Large-v3 + Gemini Vision")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Fusion v16.2")
url_input = st.text_input("Episode URL (Disney/YT/Solar):")
uploaded = st.file_uploader("OR Upload Video (Limit 200MB):", type=['mp4', 'mpeg4'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            video_path = ""
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading video file via Proxy...")
                video_path = download_video(url_input, tmp_dir)

            if not video_path:
                st.error("Failed to retrieve video. Try uploading the file directly.")
                st.stop()

            # Step 1: Whisper Transcript
            st.info("👂 OpenAI Whisper: Hearing every word...")
            audio_path = extract_audio(video_path, tmp_dir)
            with open(audio_path, "rb") as f_audio:
                raw_whisper = client_oa.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, response_format="text"
                )

            # Step 2: Gemini Vision
            st.info("☁️ Gemini Vision: Analyzing scenes...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)

            # Step 3: Fusion Prompt
            st.info(f"✍️ Authoring {pov_char}'s Chapter...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            fusion_prompt = f"""
            You are a Master Director and YA Novelist.
            CAST: {st.session_state.custom_chars}
            WHISPER TRANSCRIPT: {raw_whisper}
            
            TASK 1: Match the CAST names to the WHISPER dialogue based on the video visual.
            TASK 2: Write a full YA novel chapter from {pov_char}'s POV. 
            Include internal feelings, specific visual cues (like the leopard print/Staten Island hair), and the magic mechanics.
            
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
                st.warning("Split failed, displaying raw output.")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. THE OUTPUT ---
if st.session_state.transcript:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Verbatim Script")
        st.text_area("Source", st.session_state.transcript, height=600)
    with r:
        st.subheader(f"📖 {pov_char}'s Chapter")
        st.text_area("Manuscript", st.session_state.novel, height=600)
        # Mobile-friendly copy button
        st.download_button("💾 Download Chapter", st.session_state.novel, file_name=f"{pov_char}_Chapter.txt")
