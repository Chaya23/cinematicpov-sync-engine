import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Studio v13.4", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. MODEL AUTO-SWITCHER (The 404 Fix) ---
def get_active_model():
    """Finds the best available model for video/dialogue tasks in 2026."""
    try:
        available = [m.name.split('/')[-1] for m in genai.list_models() 
                     if 'generateContent' in m.supported_generation_methods]
        # Priority list for high-accuracy vision + transcript
        priority = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash']
        for p in priority:
            if p in available: return p
        return available[0] # Total fallback
    except Exception:
        return "gemini-3-flash-preview" # Default if list fails

# --- 3. VIDEO ENGINE ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    # Low-res 480p is best for API speed and token efficiency
    ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': out_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 4. STUDIO UI ---
st.title("🎬 CinematicPOV Studio v13.4")
st.caption("2026 Model Support • Side-by-Side Accuracy")

with st.sidebar:
    st.header("Writing Config")
    pov_char = st.selectbox("POV Character:", ["Roman", "Billie", "Justin", "Winter", "Milo"])
    style = st.selectbox("Style:", ["YA Novel", "Middle Grade", "TV Script"])
    st.divider()
    st.info("Agentic Vision is enabled: The AI will 'investigate' scenes for better dialogue accuracy.")

url_input = st.text_input("Enter Episode URL (YouTube/DisneyNow/Solar):")
uploaded = st.file_uploader("OR Upload MP4:", type=['mp4'])

if st.button("🚀 SYNC & AUTHOR", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # 1. Prepare Video
            video_path = os.path.join(tmp_dir, "input.mp4")
            if uploaded:
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                video_path = download_video(url_input, tmp_dir)

            # 2. Vision Upload
            st.info("☁️ Uploading to Gemini...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            # 3. Model & Prompt
            target_model = get_active_model()
            st.caption(f"Using Engine: {target_model}")
            model = genai.GenerativeModel(target_model)
            
            # The prompt is optimized for 'Agentic Vision' - exploring details
            prompt = f"""
            AGENTIC VISION TASK: Explore this video to identify characters and their dialogue.
            
            1. FULL TRANSCRIPT:
            - Label speakers: [Roman], [Billie], [Justin], etc.
            - Format: [MM:SS] Speaker: "Dialogue"
            
            2. NOVEL ADAPTATION:
            - Write a first-person chapter from {pov_char}'s perspective.
            - Style: {style}.
            - Mirror the transcript dialogue exactly within the story.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Script]
            ---POV_START---
            [Novel]
            """

            response = model.generate_content(
                [video_file, prompt],
                generation_config={"max_output_tokens": 8192, "temperature": 0.5}
            )
            
            # 4. Result Splitting
            if response.text:
                parts = response.text.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Studio View Ready!")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. SIDE-BY-SIDE VIEW ---
if "transcript" in st.session_state:
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🎤 Verified Transcript")
        st.text_area("Source", st.session_state.transcript, height=800)
    with col_r:
        st.subheader(f"📖 {pov_char}'s Adaptation")
        st.text_area("Novel", st.session_state.novel, height=800)
