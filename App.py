import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# ------------------- 1. CONFIGURATION & PERSISTENCE -------------------
st.set_page_config(page_title="POV Cinema Studio", layout="wide")

# Initialize session state so we don't lose files on refresh
if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

# AI Setup
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- 2. THE DVR ENGINE -------------------
def start_background_recording(url):
    """Downloads video in the background so you don't have to watch"""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"rec_{timestamp}.mp4"
    # Speed through recording by grabbing stream directly
    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "--no-playlist", "-o", filename, url]
    subprocess.Popen(cmd) 
    return filename

# ------------------- 3. MAIN INTERFACE -------------------
st.title("🎬 POV Cloud DVR & Writing Engine")

tab_queue, tab_library = st.tabs(["📥 Add to Queue", "📚 Library & Results"])

with tab_queue:
    st.info("Pasting a link here will 'Queue' the video. You don't have to watch it play!")
    video_url = st.text_input("Paste DisneyNow / YouTube URL:")
    pov_choice = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin"])
    
    if st.button("🔴 Start Background Recording"):
        if video_url:
            filename = start_background_recording(video_url)
            # Add to our library list
            st.session_state.recorded_files.append({
                "file": filename, 
                "pov": pov_choice, 
                "status": "Recording..."
            })
            st.success(f"✅ Queued: {filename}. You can close the app or go to the Library tab now.")
        else:
            st.error("Please paste a link first.")

with tab_library:
    st.subheader("Process & Test Recordings")
    
    # Manual Upload Section for existing files
    with st.expander("📂 Have a file already? Manual Upload"):
        manual_file = st.file_uploader("Upload MP4/WebM", type=["mp4", "webm"])
        if manual_file:
            with open(manual_file.name, "wb") as f:
                f.write(manual_file.getbuffer())
            if st.button("➕ Add Upload to Library"):
                st.session_state.recorded_files.append({
                    "file": manual_file.name, 
                    "pov": "Custom", 
                    "status": "Ready"
                })

    st.divider()

    # Display the Library List
    if not st.session_state.recorded_files:
        st.write("No recordings found yet.")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_name = item['file']
            
            # Check if file exists on disk yet
            if os.path.exists(file_name):
                with st.container():
                    col_info, col_play, col_write = st.columns([2, 1, 1])
                    
                    with col_info:
                        st.write(f"🎥 **{file_name}** (POV: {item['pov']})")
                    
                    with col_play:
                        # Test if video was recorded correctly
                        if st.button("📺 Play Test", key=f"play_{idx}"):
                            st.video(file_name)
                    
                    with col_write:
                        # Run the AI Production
                        if st.button("✨ Write Novel", key=f"write_{idx}"):
                            with st.status("AI Analyzing Video...") as status:
                                # 1. Upload to Gemini
                                gen_file = genai.upload_file(file_name)
                                while gen_file.state.name == "PROCESSING":
                                    time.sleep(2)
                                    gen_file = genai.get_file(gen_file.name)
                                
                                # 2. Generate
                                model = genai.GenerativeModel('gemini-1.5-pro')
                                prompt = f"""
                                Identify speakers based on visual cues.
                                TASK 1: Full Transcript.
                                TASK 2: Deep Novel Chapter from {item['pov']}'s POV.
                                Split with: ---SPLIT---
                                """
                                resp = model.generate_content([gen_file, prompt])
                                
                                # 3. Parse and Display in separate boxes
                                if "---SPLIT---" in resp.text:
                                    parts = resp.text.split("---SPLIT---")
                                    st.subheader("📜 Transcript (T-Box)")
                                    st.text_area("Transcript", parts[0], height=250)
                                    st.subheader("📖 Novel (N-Box)")
                                    st.text_area("Novel", parts[1], height=400)
                                else:
                                    st.write(resp.text)
            else:
                st.write(f"⏳ {file_name} is still downloading/recording...")

