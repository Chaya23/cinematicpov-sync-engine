import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
raw_key = st.secrets.get("GEMINI_API_KEY", "")
if raw_key:
    genai.configure(api_key=raw_key.strip())
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

# --- THE FIX: CLEAN SAFETY SETTINGS ---
# We only use the 4 standard categories that Google always accepts.
# Civic Integrity is removed because it causes the 400 error on many projects.
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# 2. PERSISTENCE
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# 3. PRODUCTION ENGINE
t_up, t_url = st.tabs(["📁 File Upload", "🌐 URL Sync"])
with t_up:
    file_vid = st.file_uploader("Upload MP4", type=["mp4"])
with t_url:
    url_link = st.text_input("Paste Link")

if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Processing with Validated Safety...") as status:
        try:
            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            model = genai.GenerativeModel('gemini-1.5-flash')
            genai_file = genai.upload_file(path=source)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = "TASK 1: VERBATIM TRANSCRIPT. ---SPLIT--- TASK 2: 2500-word Novel Chapter."
            
            # Applying the fixed safety settings
            response = model.generate_content(
                [genai_file, prompt], 
                safety_settings=safety_settings
            )
            
            if response.candidates:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0].strip(), parts[1].strip()
                else:
                    st.session_state.chapter = full_text
                st.rerun()
            else:
                st.error("AI still blocked the request. Try a shorter or cleaner clip.")

        except Exception as e:
            st.error(f"Error: {e}")

# 4. RESULTS
if st.session_state.chapter:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📜 Transcript")
        st.text_area("T-Preview", st.session_state.transcript, height=300)
    with c2:
        st.subheader("📖 Novel")
        st.text_area("N-Preview", st.session_state.chapter, height=300)
