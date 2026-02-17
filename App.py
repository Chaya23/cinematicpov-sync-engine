import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# ------------------- 1. CONFIG & STYLING -------------------
st.set_page_config(page_title="POV Cloud DVR", layout="wide")

# AI Setup
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- 2. THE BACKGROUND ENGINE -------------------
def queue_recording(url, pov_name):
    """
    Simulates a Cloud DVR. It starts a background process 
    so you can close the app while it 'records'.
    """
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"rec_{timestamp}.mp4"
    
    # This command runs in the background (yt-dlp)
    # It speeds through by grabbing the direct stream
    cmd = [
        "yt-dlp", 
        "-f", "best[ext=mp4]", 
        "--no-playlist", 
        "-o", filename, 
        url
    ]
    
    process = subprocess.Popen(cmd)
    return filename, process

# ------------------- 3. THE INTERFACE -------------------
st.title("☁️ POV Cloud DVR & Writing Engine")
st.info("Pasting a link here will 'Queue' the video. You don't have to watch it play!")

# Sidebar for Character Settings
with st.sidebar:
    st.header("👤 Narrator Settings")
    pov_choice = st.radio("Who is telling the story?", ["Roman", "Billie", "Justin"])
    st.write("---")
    st.subheader("Queue Status")
    if "job_running" in st.session_state and st.session_state.job_running:
        st.warning("🟡 Recording in progress...")
    else:
        st.success("🟢 Ready for new task")

# MAIN TABS
tab_queue, tab_library = st.tabs(["📥 Add to Queue", "📚 Finished Chapters"])

with tab_queue:
    video_url = st.text_input("Paste DisneyNow / YouTube / URL here:")
    
    if st.button("🔴 Start Background Recording"):
        if video_url:
            with st.status("Adding to Cloud Queue...") as status:
                filename, proc = queue_recording(video_url, pov_choice)
                st.session_state.current_file = filename
                st.session_state.job_running = True
                
                status.update(label="✅ Queued! You can close the app now.", state="complete")
                st.toast(f"Recording {filename} in background...")
        else:
            st.error("Please paste a link first!")

with tab_library:
    st.subheader("Your Processed Fanfics")
    
    # Check if a file finished downloading
    if "current_file" in st.session_state:
        file_path = st.session_state.current_file
        
        if os.path.exists(file_path):
            st.success(f"🎬 Recording Finished: {file_path}")
            
            if st.button("✨ Write Novel Chapter Now"):
                with st.spinner("AI is analyzing the recording..."):
                    # 1. Upload to AI
                    video_file = genai.upload_file(file_path)
                    while video_file.state.name == "PROCESSING":
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)
                    
                    # 2. Generate Transcript and Story
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    prompt = f"""
                    Task 1: Full Transcript with timestamps.
                    Task 2: Novel Chapter from {pov_choice}'s POV. 
                    Split them with '---SPLIT---'.
                    """
                    response = model.generate_content([video_file, prompt])
                    
                    # 3. Display Results
                    parts = response.text.split("---SPLIT---")
                    st.session_state.results = parts
                    st.session_state.job_running = False

    # Show results if they exist
    if "results" in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📜 Transcript")
            st.text_area("T-Box", st.session_state.results[0], height=400)
        with col2:
            st.subheader(f"📖 {pov_choice}'s Novel")
            st.text_area("N-Box", st.session_state.results[1] if len(st.session_state.results) > 1 else "", height=400)
