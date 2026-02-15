import streamlit as st
import os
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
from streamlit_webrtc import webrtc_streamer

# 1. SETUP & SECRETS
load_dotenv()
# This looks for your key in GitHub Secrets OR a local .env file
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("Missing Gemini API Key! Add it to Streamlit Secrets.")

# 2. MOBILE-FIRST UI
st.set_page_config(page_title="Roman's Redemption", page_icon="🪄")
st.title("🧙‍♂️ Roman's Redemption")
st.caption("Mobile Studio v2.0 - Unlimited Edition")

# --- TABBED NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["🔗 Links", "📱 Live DVR", "📂 Upload"])

# TAB 1: DISNEY NOW / YOUTUBE DOWNLOADER
with tab1:
    st.subheader("Process Link")
    video_url = st.text_input("Paste Disney Now or YT URL:")
    if st.button("Download & Novelize"):
        with st.status("🎬 Extracting magic from link...") as s:
            # -x extracts audio only to save space/time
            cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", "source_audio.mp3", video_url]
            subprocess.run(cmd)
            s.update(label="✅ Audio Captured. Writing chapter...", state="complete")
        st.success("Roman's POV is being generated...")

# TAB 2: LIVE MOBILE DVR (Quiet Recording)
with tab2:
    st.subheader("Mobile DVR")
    st.write("Record directly into the app. (Requires HTTPS)")
    # This captures video/audio directly from your phone's camera
    webrtc_streamer(
        key="mobile-dvr",
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": True}
    )

# TAB 3: UNLIMITED UPLOAD
with tab3:
    st.subheader("Local File Upload")
    st.info("Limit: 10GB (Set in config.toml)")
    up_file = st.file_uploader("Upload Movie:", type=["mp4", "mov", "mkv"])
    if up_file:
        st.write(f"📂 File Ready: {up_file.name}")
        if st.button("Start AI Production"):
            # Process the file here
            st.toast("Transcribing... this takes a few minutes.")
