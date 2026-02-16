import streamlit as st
import os
import subprocess
import google.generativeai as genai

# 1. Initialize Session State so we don't lose data on crash
if "novel_ready" not in st.session_state:
    st.session_state.novel_ready = False
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

# Setup Gemini
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🧙‍♂️ Roman's Redemption")

# TAB SYSTEM
tab1, tab2 = st.tabs(["🔗 Background Download", "📱 DVR Upload"])

with tab1:
    url = st.text_input("Disney Now / YouTube Link:")
    if st.button("🚀 Start Silent Download"):
        with st.status("📥 Server is capturing data...") as s:
            # Downloading directly to server prevents mobile crashes
            subprocess.run(["yt-dlp", "-f", "bestaudio", "-o", "temp.mp3", url])
            st.session_state.novel_ready = True
            st.session_state.transcript = "Download Complete. Ready to Novelize."
            s.update(label="✅ Captured!", state="complete")

with tab2:
    up_file = st.file_uploader("Upload 4K Record", type=["mp4", "mov"])
    if up_file:
        # Save to server immediately to prevent 'redacted' errors
        with open("raw.mp4", "wb") as f:
            f.write(up_file.getbuffer())
        
        if st.button("✍️ Novelize Upload"):
            with st.spinner("Compressing & Writing..."):
                # Use FFmpeg to shrink file to avoid memory leaks
                subprocess.run("ffmpeg -i raw.mp4 -vcodec libx264 -crf 28 -y small.mp4", shell=True)
                st.session_state.novel_ready = True
                st.session_state.transcript = "Roman Russo is writing your story..."

# --- PERSISTENT RESULT AREA ---
# This stays visible even if you refresh or switch apps
if st.session_state.novel_ready:
    st.divider()
    st.subheader("📖 Production Result")
    st.write(st.session_state.transcript)
    if st.button("🗑️ Clear & Start New"):
        st.session_state.novel_ready = False
        st.rerun()
