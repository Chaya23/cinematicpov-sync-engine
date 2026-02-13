import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v16.1", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Ensure both GOOGLE_API_KEY and OPENAI_API_KEY are in Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. THE MODEL DISCOVERY (404 FIX) ---
def get_working_model():
    """Dynamically finds the correct 2026 model ID to avoid 404s."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer Flash for 2026 stability and speed
        for target in ['gemini-3-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-flash']:
            for m in models:
                if target in m: return m
        return models[0] # Absolute fallback
    except Exception:
        return "models/gemini-1.5-flash" # Default fallback

# --- 3. THE UTILITIES ---
def extract_audio(video_path, tmp_dir):
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    command = f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y"
    subprocess.run(command, shell=True, check=True, capture_output=True)
    return audio_path

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': out_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 4. SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🎭 Character Manager")
    st.session_state.custom_chars = st.text_area("Edit Cast Names:", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    st.divider()
    st.header("✍️ Author Config")
    pov_char = st.selectbox("POV Character:", char_list)
    style = st.selectbox("Writing Style:", ["Young Adult Novel", "Middle Grade Fantasy", "Gothic Romance"])
    
    st.info("Engine: OpenAI Whisper v3 + Gemini 3 Flash Vision")

# --- 5. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Fusion v16.1")
url_input = st.text_input("Episode URL (Disney/YT):")
uploaded = st.file_uploader("OR Upload Video:", type=['mp4'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            video_path = os.path.join(tmp_dir, "input.mp4")
            if uploaded:
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading video file...")
                video_path = download_video(url_input, tmp_dir)

            # Step 1: Whisper Verbatim Audio
            st.info("👂 OpenAI Whisper: Transcribing every word...")
            audio_path = extract_audio(video_path, tmp_dir)
            with open(audio_path, "rb") as f_audio:
                raw_whisper = client_oa.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, response_format="text"
                )

            # Step 2: Gemini Vision Analysis
            st.info("☁️ Gemini Vision: Analyzing scenes...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)

            # Step 3: Fusion & Authoring
            st.info(f"✍️ Authoring {pov_char}'s Full Chapter...")
            model_name = get_working_model()
            model = genai.GenerativeModel(model_name)
            
            fusion_prompt = f"""
            You are a Master Director and YA Novelist.
            CAST: {st.session_state.custom_chars}
            WHISPER TRANSCRIPT: {raw_whisper}
            
            TASK 1: VERIFIED SCRIPT
            Match the names in the CAST to the lines in the WHISPER TRANSCRIPT by watching the video to see who is speaking.
            Format: [Name]: "Dialogue"
            
            TASK 2: NOVEL CHAPTER
            Write a long, immersive first-person chapter from {pov_char}'s POV in a {style} style.
            - Match the dialogue EXACTLY to the transcript.
            - Focus on internal thoughts, feelings, and sensory descriptions (like the leopard print and being stuck to Winter).
            
            FORMAT:
            ---SCRIPT_START---
            [Named Dialogue]
            ---NOVEL_START---
            [Full Chapter]
            """
            
            response = model.generate_content([video_file, fusion_prompt])
            
            if response.text:
                parts = response.text.split("---NOVEL_START---")
                st.session_state.transcript = parts[0].replace("---SCRIPT_START---", "")
                st.session_state.novel = parts[1] if len(parts) > 1 else "Novel part missing."
                st.success("✅ Fusion Complete!")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 6. STUDIO OUTPUT ---
if st.session_state.transcript:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Verbatim Named Script")
        st.text_area("Source", st.session_state.transcript, height=800, key="scr_f")
    with r:
        st.subheader(f"📖 {pov_char}'s Novel Chapter")
        st.text_area("Manuscript", st.session_state.novel, height=800, key="nov_f")
