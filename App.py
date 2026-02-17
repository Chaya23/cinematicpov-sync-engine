import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
import shutil
from datetime import datetime

# ------------------- 1. CONFIG -------------------
st.set_page_config(page_title="POV DVR Studio", layout="wide")

# Use gemini-2.0-flash (most stable in early 2026)
MODEL_NAME = "gemini-2.0-flash" 

if "library" not in st.session_state:
    st.session_state.library = []
if "staged_file" not in st.session_state:
    st.session_state.staged_file = None

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- 2. CLEANUP UTILITY -------------------
def clear_disk():
    """Deletes all local mp4s to prevent the 1GB RAM crash"""
    for f in os.listdir("."):
        if f.endswith(".mp4"):
            os.remove(f)
    st.session_state.library = []
    st.session_state.staged_file = None
    st.rerun()

# ------------------- 3. UI -------------------
st.title("🎬 POV Cloud DVR")

# Sidebar Cleanup (Vital for mobile stability)
with st.sidebar:
    st.header("⚙️ System Tools")
    if st.button("🗑️ Delete All & Reset"):
        clear_disk()
    st.caption("Tip: If the app slows down, click Reset to clear memory.")

tab_rec, tab_lib = st.tabs(["🔴 Recorder", "📚 Library"])

with tab_rec:
    u = st.text_input("Video Link:")
    if st.button("🚀 Start Recording"):
        ts = datetime.now().strftime("%H%M%S")
        fn = f"dvr_{ts}.mp4"
        # Force mobile-friendly H.264
        cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, u]
        with st.status("DVR Recording..."):
            subprocess.run(cmd)
            st.session_state.library.append(fn)
        st.success(f"Saved {fn}!")

with tab_lib:
    if not st.session_state.library:
        st.info("No videos recorded yet.")
    else:
        for idx, video_fn in enumerate(st.session_state.library):
            with st.container(border=True):
                st.write(f"🎞️ **{video_fn}**")
                
                col1, col2 = st.columns(2)
                
                # STEP 1: PREPARE (This saves RAM)
                if col1.button(f"🔍 Prepare Download", key=f"prep_{idx}"):
                    st.session_state.staged_file = video_fn
                
                # STEP 2: DOWNLOAD (Only shows for the one you prepared)
                if st.session_state.staged_file == video_fn:
                    with open(video_fn, "rb") as f:
                        col2.download_button(
                            label="📥 Save to Phone",
                            data=f,
                            file_name=video_fn,
                            mime="video/mp4",
                            key=f"dl_{idx}"
                        )
                    st.toast("File ready for download!", icon="✅")

                # AI PROD BOXES
                if st.button("✨ Write Novel", key=f"ai_{idx}"):
                    with st.status("AI Analyzing..."):
                        gf = genai.upload_file(video_fn)
                        while gf.state.name == "PROCESSING": time.sleep(2); gf = genai.get_file(gf.name)
                        m = genai.GenerativeModel(MODEL_NAME)
                        res = m.generate_content([gf, "Write Transcript and Novel chapter. Split with '---'"]).text.split("---")
                        
                        st.subheader("📜 Transcript (T-Box)")
                        st.text_area("T", res[0], height=200)
                        st.subheader("📖 Novel (N-Box)")
                        st.text_area("N", res[1] if len(res)>1 else "", height=300)
