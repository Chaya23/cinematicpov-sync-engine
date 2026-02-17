import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# ------------------- 1. CONFIG & SESSION STATE -------------------
st.set_page_config(page_title="POV Cinema Studio", layout="wide", page_icon="🎬")

# Initialize session state so we don't lose data on refresh
if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 Error: Missing GEMINI_API_KEY in Streamlit Secrets!")

# ------------------- 2. THE DVR ENGINE (BACKGROUND) -------------------
def start_dvr(url, pov_name):
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"rec_{timestamp}.mp4"
    log_file = f"log_{filename}.txt"
    
    # We use Popen so the app keeps running while the video downloads
    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "--no-playlist", "-o", filename, url]
    
    with open(log_file, "w") as f:
        subprocess.Popen(cmd, stdout=f, stderr=f)
    
    return filename, log_file

# ------------------- 3. MAIN INTERFACE -------------------
st.title("☁️ POV Cloud DVR & Writing Engine")

tab_queue, tab_library = st.tabs(["📥 Add to Queue", "📚 Library & Results"])

# --- TAB 1: QUEUE ---
with tab_queue:
    st.info("Pasting a link here starts a background 'Cloud Recording'. You can close the app and return later.")
    video_url = st.text_input("Paste DisneyNow / YouTube URL:")
    pov_choice = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin", "Milo"])
    
    if st.button("🔴 Start Background Recording"):
        if video_url:
            fn, log = start_dvr(video_url, pov_choice)
            st.session_state.recorded_files.append({
                "file": fn, 
                "log": log, 
                "pov": pov_choice,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            st.success(f"Successfully Queued: {fn}")
            st.toast("Recording started in background!")
        else:
            st.error("Please paste a link first!")

# --- TAB 2: LIBRARY ---
with tab_library:
    # Manual Refresh button to check for finished files
    if st.button("🔄 Check for Finished Recordings"):
        st.rerun()

    if not st.session_state.recorded_files:
        st.write("No recordings in queue. Go to 'Add to Queue' to start.")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_name = item['file']
            log_name = item['log']
            
            with st.container(border=True):
                col_info, col_play, col_write = st.columns([2, 1, 1])
                
                with col_info:
                    st.write(f"🎥 **{file_name}**")
                    st.caption(f"POV: {item['pov']} | Added: {item['created_at']}")
                
                # Check if file exists (it's finished downloading)
                if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
                    with col_play:
                        if st.button("📺 Play Test", key=f"play_{idx}"):
                            st.video(file_name)
                    
                    with col_write:
                        if st.button("✍️ Write Story", key=f"write_{idx}"):
                            with st.status("AI is analyzing the footage...", expanded=True) as status:
                                # 1. Upload to Gemini
                                status.write("Uploading video to Google AI...")
                                video_file = genai.upload_file(file_name)
                                while video_file.state.name == "PROCESSING":
                                    time.sleep(2)
                                    video_file = genai.get_file(video_file.name)
                                
                                # 2. Generate
                                status.write("Generating Transcript and Novel Chapter...")
                                model = genai.GenerativeModel('gemini-1.5-pro')
                                prompt = f"POV: {item['pov']}. 1: Full Transcript. 2: Novel Chapter. Split with ---SPLIT---"
                                response = model.generate_content([video_file, prompt])
                                
                                # 3. Split and Store
                                parts = response.text.split("---SPLIT---")
                                st.session_state[f"res_{idx}"] = parts
                                status.update(label="✅ Finished!", state="complete")

                    # Show Results if they exist for this file
                    if f"res_{idx}" in st.session_state:
                        res = st.session_state[f"res_{idx}"]
                        st.divider()
                        res_col1, res_col2 = st.columns(2)
                        with res_col1:
                            st.subheader("📜 Transcript (T-Box)")
                            st.text_area("Transcript", res[0], height=300, key=f"t_{idx}")
                        with res_col2:
                            st.subheader(f"📖 {item['pov']}'s Chapter (N-Box)")
                            st.text_area("Novel", res[1] if len(res)>1 else "", height=300, key=f"n_{idx}")
                
                else:
                    # Show progress from the log file
                    st.warning("⏳ Still Downloading...")
                    if os.path.exists(log_name):
                        with st.expander("View Recording Logs"):
                            with open(log_name, "r") as f:
                                st.code(f.read()[-500:], language="text") # Show last 500 chars
