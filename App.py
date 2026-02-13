import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. SETUP & PERSISTENCE ---
st.set_page_config(page_title="CinematicPOV v14.0", layout="wide", page_icon="🎬")

# Timeout fix: Streamlit keeps state in 'st.session_state' even if the page flickers
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. ENGINE UTILITIES ---
def get_active_model():
    try:
        available = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-1.5-pro'] # Pro for better story length
        for p in priority:
            if p in available: return p
        return "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': out_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. SIDEBAR: CHARACTER MANAGER ---
with st.sidebar:
    st.header("🎭 Character Manager")
    st.session_state.custom_chars = st.text_area("Edit Cast (Comma separated):", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    st.divider()
    st.header("✍️ Writing Config")
    pov_char = st.selectbox("Select POV:", char_list)
    style = st.selectbox("Style:", ["YA Novel (Sarah J. Maas)", "Middle Grade (Percy Jackson)", "Dark Fantasy"])
    
    st.divider()
    st.info("Dual-Stage Processing: Enabled (Transcript + Novel generated separately to prevent cut-offs).")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Studio v14.0")
url_input = st.text_input("Episode URL:")
uploaded = st.file_uploader("OR Upload MP4:", type=['mp4'])

if st.button("🚀 START SYNC (STAGED)", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            video_path = os.path.join(tmp_dir, "input.mp4")
            if uploaded:
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                video_path = download_video(url_input, tmp_dir)

            st.info("☁️ Uploading to Vision...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            model_id = get_active_model()
            model = genai.GenerativeModel(model_id)
            
            # STAGE 1: THE FULL SCRIPT (Verbatim)
            st.info("🎤 Stage 1: Transcribing Dialogue...")
            t_prompt = f"Identify these characters: {st.session_state.custom_chars}. Extract EVERY line of dialogue verbatim with [MM:SS] timestamps."
            t_response = model.generate_content([video_file, t_prompt], generation_config={"max_output_tokens": 4000})
            st.session_state.transcript = t_response.text

            # STAGE 2: THE NOVEL (Creative)
            st.info(f"📖 Stage 2: Authoring {pov_char}'s Chapter...")
            n_prompt = f"Based on the video, write a long first-person novel chapter from {pov_char}'s POV in {style} style. Use deep internal monologue and sensory details."
            n_response = model.generate_content([video_file, n_prompt], generation_config={"max_output_tokens": 4000})
            st.session_state.novel = n_response.text

            st.success("✅ Both Stages Complete!")
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. THE STUDIO DISPLAY ---
if st.session_state.transcript:
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🎤 Verified Transcript")
        st.text_area("Full Script", st.session_state.transcript, height=800, key="t_output")
    with col_r:
        st.subheader(f"📖 {pov_char}'s Novel Chapter")
        st.text_area("Manuscript", st.session_state.novel, height=800, key="n_output")
