import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
import tempfile
import traceback
from datetime import datetime

# ------------------- 1. CONFIG & REFRESH -------------------
st.set_page_config(page_title="POV Cinema Studio 2026", layout="wide", page_icon="🎬")

# SESSION STATE: Keeps your files and results alive
if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

# API SETUP (FIXED MODEL NAME FOR 2026)
# Gemini 1.5 is discontinued. We now use 2.0-flash for high-speed tasks.
MODEL_NAME = "gemini-2.0-flash" 

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 Error: Missing GEMINI_API_KEY in Secrets!")

# ------------------- 2. THE DVR ENGINE (UNRESTRICTED) -------------------
def start_dvr(url, cookies_file=None):
    """
    Simulates PlayOn 'Cloud Recording'. 
    Grabs the video in the background so you don't have to watch.
    """
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"rec_{timestamp}.mp4"
    log_file = f"log_{filename}.txt"
    
    # UNRESTRICTED: No blocked_hints here.
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "best[ext=mp4]", 
        "-o", filename,
        url
    ]
    
    # Use cookies for sites like DisneyNow/YouTube
    if cookies_file:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])
    
    # Run silently in background
    with open(log_file, "w") as f:
        subprocess.Popen(cmd, stdout=f, stderr=f)
    
    return filename, log_file

# ------------------- 3. INTERFACE -------------------
st.title("🎬 POV Cloud DVR & Production Studio")
st.caption("Universal Recording → AI Analysis → Roman's Fanfic POV")

tab_queue, tab_library = st.tabs(["📥 Add to Queue", "📚 Library & Results"])

with tab_queue:
    st.info("Paste a link to queue a 'Cloud Recording'. It speeds through the data in the background.")
    video_url = st.text_input("Paste Video URL (YouTube, Disney, etc.):")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pov_choice = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin", "Milo"])
    with col_b:
        cookie_upload = st.file_uploader("🍪 Upload cookies.txt (Optional)", type=["txt"])

    if st.button("🔴 Start Background Recording", use_container_width=True):
        if video_url:
            fn, log = start_dvr(video_url, cookie_upload)
            st.session_state.recorded_files.append({
                "file": fn, "log": log, "pov": pov_choice, "status": "Recording"
            })
            st.success(f"Successfully Queued: {fn}. You can close the app now.")
        else:
            st.error("Please paste a link first!")

with tab_library:
    if st.button("🔄 Refresh Status"):
        st.rerun()

    if not st.session_state.recorded_files:
        st.write("No active recordings. Queue one up!")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_name = item['file']
            log_name = item['log']
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"🎥 **{file_name}**")
                    st.caption(f"Target POV: {item['pov']}")
                
                # Check if file is ready
                if os.path.exists(file_name) and os.path.getsize(file_name) > 1000:
                    with col2:
                        if st.button("📺 Play Test", key=f"play_{idx}"):
                            st.video(file_name)
                    with col3:
                        if st.button("✨ Write Novel", key=f"write_{idx}"):
                            with st.status("AI Analyzing Video...", expanded=True) as status:
                                try:
                                    # 1. Upload to Google (2026 way)
                                    status.write("Uploading file to AI...")
                                    gen_file = genai.upload_file(file_name)
                                    while gen_file.state.name == "PROCESSING":
                                        time.sleep(2)
                                        gen_file = genai.get_file(gen_file.name)
                                    
                                    # 2. Use Gemini 2.0-Flash (Fixed 404)
                                    status.write(f"AI is watching with {MODEL_NAME}...")
                                    model = genai.GenerativeModel(MODEL_NAME)
                                    prompt = f"""
                                    Identify characters from 'Wizards Beyond Waverly Place'.
                                    TASK 1: Write a full transcript with speaker names.
                                    TASK 2: Write a detailed novel chapter from {item['pov']}'s perspective.
                                    Split the sections with '---SPLIT---'
                                    """
                                    response = model.generate_content([gen_file, prompt])
                                    
                                    # Store results in session state
                                    st.session_state[f"res_{idx}"] = response.text.split("---SPLIT---")
                                    status.update(label="✅ Success!", state="complete")
                                except Exception as e:
                                    st.error(f"AI Error: {str(e)}")
                                    st.code(traceback.format_exc())
                else:
                    st.warning("⏳ Still Downloading in background...")
                    with st.expander("Check Progress Log"):
                        if os.path.exists(log_name):
                            with open(log_name, "r") as f:
                                st.code(f.read()[-500:]) # Last few lines of log

                # --- THE RESULT BOXES (T-BOX & N-BOX) ---
                if f"res_{idx}" in st.session_state:
                    res = st.session_state[f"res_{idx}"]
                    st.divider()
                    box1, box2 = st.columns(2)
                    with box1:
                        st.subheader("📜 Transcript (T-Box)")
                        st.text_area("T-Text", res[0], height=300, key=f"t_{idx}")
                    with box2:
                        st.subheader(f"📖 {item['pov']}'s Novel (N-Box)")
                        st.text_area("N-Text", res[1] if len(res)>1 else "", height=300, key=f"n_{idx}")
