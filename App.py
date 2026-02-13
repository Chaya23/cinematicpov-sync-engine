import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. CONFIG ---
st.set_page_config(page_title="CinematicPOV: Verified Studio", layout="wide", page_icon="✍️")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE ENGINE ---
def generate_studio_content(model, content):
    """Generates the dual-view with retry logic for 429s."""
    for attempt in range(4):
        try:
            return model.generate_content(
                content, 
                generation_config={
                    "temperature": 0.4, # Lower temp = more accurate dialogue
                    "max_output_tokens": 8192
                }
            )
        except exceptions.ResourceExhausted:
            time.sleep((2 ** attempt) + 1)
    return None

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', # High-accuracy 480p
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. UI ---
st.title("✍️ CinematicPOV: Verified Studio v13.1")
st.caption("Synchronized Dialogue Tracking + Character ID")

with st.expander("⚙️ Studio Settings", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        url_input = st.text_input("Source URL:")
        uploaded = st.file_uploader("Upload Video:", type=['mp4'])
    with col2:
        pov_char = st.selectbox("POV Character:", ["Roman", "Billie", "Justin", "Winter", "Milo"])
        style = st.selectbox("Narrative Style:", ["YA Novel (S.J. Maas)", "Middle Grade (Percy Jackson)"])

if st.button("🚀 SYNC & AUTHOR", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                video_path = download_video(url_input, tmp_dir)

            st.info("☁️ Vision Engine analyzing speakers...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # The "Verification" Prompt
            prompt = f"""
            Identify all characters visually. Match every line of spoken dialogue to the correct name.
            
            1. FULL TRANSCRIPT:
            - Format: [MM:SS] Name: "Dialogue"
            - Include every single word spoken.
            
            2. NOVEL CHAPTER:
            - Write a detailed first-person chapter for {pov_char}.
            - Ensure all dialogue from the transcript is accurately reflected.
            - Style: {style}.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Insert Time-Stamped Script]
            ---POV_START---
            [Insert Novel]
            """

            response = generate_studio_content(model, [video_file, prompt])
            
            if response and response.text:
                parts = response.text.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Studio View Ready!")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. THE SIDE-BY-SIDE STUDIO ---
if "transcript" in st.session_state:
    st.divider()
    left, right = st.columns(2)
    
    with left:
        st.subheader("🎤 Verified Transcript")
        st.markdown("*Use this to check character names and dialogue.*")
        st.text_area("Source", st.session_state.transcript, height=800, label_visibility="collapsed")
        
    with right:
        st.subheader(f"📖 {pov_char}'s Adaptation")
        st.markdown(f"*The {style} version of the scenes above.*")
        st.text_area("Novel", st.session_state.novel, height=800, label_visibility="collapsed")
