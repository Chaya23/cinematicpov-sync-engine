import os
import sys
import time
import tempfile
import subprocess
import traceback
import streamlit as st
import google.generativeai as genai

# ---------------- 1. CONFIG & SESSION STATE ----------------
st.set_page_config(page_title="🎬 CastScript AI Pro", layout="wide", page_icon="🎬")

# Ensure results persist
if "final_transcript" not in st.session_state:
    st.session_state.final_transcript = ""
if "final_pov" not in st.session_state:
    st.session_state.final_pov = ""

# AI Setup
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ---------------- 2. REMOVED RESTRICTIONS & DVR ENGINE ----------------
# Blocklist removed as requested.

def download_video(url, output_path, cookies_file=None):
    """Downloads video using yt-dlp. Uses cookies to bypass login screens."""
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "best[ext=mp4]", 
        "-o", output_path,
        url,
    ]
    
    # If user provides cookies.txt, use it to bypass blocks
    if cookies_file:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])
        
    subprocess.run(cmd, check=True)

# ---------------- 3. THE ENGINE LOGIC (Merged for zero-import errors) ----------------
class SimpleEngine:
    def __init__(self):
        pass

    def rewrite_pov(self, transcript, character_name, cast_info):
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"""
        CAST: {cast_info}
        POV CHARACTER: {character_name}
        
        TRANSCRIPT:
        {transcript}
        
        TASK: Convert this transcript into a first-person novel chapter from {character_name}'s perspective.
        """
        response = model.generate_content(prompt)
        return response.text

# ---------------- 4. UI INTERFACE ----------------
st.title("🎬 CastScript AI: Unrestricted Mode")
st.caption("Universal Video → AI Analysis → POV Rewrite")

with st.sidebar:
    st.header("⚙️ Settings")
    cast_info = st.text_area("Cast (Name - Role)", "Roman - Younger brother\nBillie - Teen girl", height=150)
    pov_name = st.text_input("Narrator POV", "Roman")
    
    st.divider()
    cookie_upload = st.file_uploader("🍪 Upload cookies.txt (For DisneyNow/YouTube)", type=["txt"])

# --- INPUT SECTION ---
st.subheader("📥 Input")
url = st.text_input("Paste URL (Any site supported by yt-dlp)")
uploaded_file = st.file_uploader("Or upload video", type=["mp4", "mkv", "webm"])

if st.button("🚀 Run Production", use_container_width=True):
    if not url and not uploaded_file:
        st.error("Please provide a source.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "input.mp4")
            
            try:
                # Get the video
                if uploaded_file:
                    with open(video_path, "wb") as f:
                        f.write(uploaded_file.read())
                else:
                    with st.status("📥 Recording/Downloading..."):
                        download_video(url, video_path, cookie_upload)
                
                # AI Processing
                with st.status("🧠 AI is watching & writing..."):
                    # 1. Upload to Gemini for Transcript
                    gen_file = genai.upload_file(video_path)
                    while gen_file.state.name == "PROCESSING":
                        time.sleep(2)
                        gen_file = genai.get_file(gen_file.name)
                    
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    t_resp = model.generate_content([gen_file, "Write a full transcript with speaker names."])
                    st.session_state.final_transcript = t_resp.text
                    
                    # 2. POV Rewrite
                    engine = SimpleEngine()
                    st.session_state.final_pov = engine.rewrite_pov(
                        st.session_state.final_transcript, pov_name, cast_info
                    )
                
                st.success("✅ Finished!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.code(traceback.format_exc())

# --- OUTPUT SECTION ---
if st.session_state.final_transcript:
    tab1, tab2 = st.tabs(["📜 Transcript (T-Box)", "📖 Novel (N-Box)"])
    with tab1:
        st.text_area("Transcript", st.session_state.final_transcript, height=400)
    with tab2:
        st.text_area(f"POV: {pov_name}", st.session_state.final_pov, height=400)
