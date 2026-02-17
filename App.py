import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
import traceback
from datetime import datetime

# ------------------- 1. CONFIG & REFRESH -------------------
st.set_page_config(page_title="POV DVR Engine", layout="wide", page_icon="📽️")

if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

# FIX: Use Gemini 2.0-Flash to avoid 404
MODEL_NAME = "gemini-2.0-flash" 
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- 2. THE DVR ENGINE (FORCE MP4) -------------------
def run_dvr_with_progress(url, cookies_file=None):
    """Downloads and merges into a REAL MP4 with live log output."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"dvr_rec_{timestamp}.mp4"
    log_file = f"log_{timestamp}.txt"
    
    # 2026 Pro Flags: Force MP4 merge and H.264/AAC for max compatibility
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", filename,
        url
    ]
    
    if cookies_file:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])

    # We use st.status to show the "Figure Running"
    with st.status(f"🎬 DVR Recording: {filename}", expanded=True) as status:
        st.write("Initializing stream...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # This loop reads the yt-dlp output and shows it in the app live!
        log_display = st.empty()
        full_log = ""
        for line in process.stdout:
            full_log += line
            log_display.code(line) # Show the last line of the download
            if "[download] 100%" in line:
                st.write("Merging Video & Audio... (FFmpeg running)")
        
        process.wait()
        if process.returncode == 0:
            status.update(label="✅ Recording Saved Successfully!", state="complete")
            return filename
        else:
            status.update(label="❌ Recording Failed", state="error")
            st.error(full_log[-500:]) # Show the last bit of the error log
            return None

# ------------------- 3. UI INTERFACE -------------------
st.title("🎬 POV Cloud DVR Studio")

tab_record, tab_library = st.tabs(["🔴 New Recording", "📚 Library"])

with tab_record:
    url = st.text_input("Paste Link (DisneyNow, YouTube, etc.):")
    pov = st.selectbox("Novel POV:", ["Roman", "Billie", "Milo"])
    cookies = st.file_uploader("🍪 cookies.txt (Upload for Disney/Netflix)", type=["txt"])
    
    if st.button("🚀 Start DVR Process"):
        if url:
            saved_file = run_dvr_with_progress(url, cookies)
            if saved_file:
                st.session_state.recorded_files.append({"file": saved_file, "pov": pov})
                st.balloons()
        else:
            st.error("Please enter a URL.")

with tab_library:
    if not st.session_state.recorded_files:
        st.info("Your library is empty. Start a recording!")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_path = item['file']
            if os.path.exists(file_path):
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    col_info.write(f"🎞️ **{file_path}**")
                    col_info.caption(f"Target POV: {item['pov']}")
                    
                    if col_btn.button("✨ Run AI Production", key=f"ai_{idx}"):
                        with st.status("AI is watching the recording...") as status:
                            # 1. Upload
                            video_file = genai.upload_file(file_path)
                            while video_file.state.name == "PROCESSING":
                                time.sleep(2)
                                video_file = genai.get_file(video_file.name)
                            
                            # 2. Write (T-Box and N-Box)
                            model = genai.GenerativeModel(MODEL_NAME)
                            prompt = f"POV: {item['pov']}. Write 1: Transcript. 2: Novel Chapter. Split with: ---"
                            resp = model.generate_content([video_file, prompt])
                            
                            parts = resp.text.split("---")
                            st.subheader("📜 Transcript")
                            st.text_area("T-Box", parts[0], height=200)
                            st.subheader(f"📖 {item['pov']}'s Novel")
                            st.text_area("N-Box", parts[1] if len(parts)>1 else "", height=300)
                            status.update(label="✅ Production Complete!", state="complete")
            else:
                st.error(f"Missing file: {file_path}")
