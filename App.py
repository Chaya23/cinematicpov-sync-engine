import streamlit as st
import google.generativeai as genai
import time
import subprocess
import os
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- THE FIX: ENSURE THESE VALUES PERSIST ---
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""
if "processed" not in st.session_state: st.session_state.processed = False

# 2. SEPARATE EXPORT ENGINE
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 3. SIDEBAR: THE CAST BIBLE
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Update Cast Roles:", 
        "Giada: Mother (Mortal)\nJustin: Father (Wizard)\nRoman: Protagonist (Son)\nTheresa: Grandmother\nBillie: Protagonist (Sister)")
    pov_choice = st.selectbox("Novel Narrator:", ["Roman Russo", "Billie", "Justin"])
    st.divider()
    cookie_file = st.file_uploader("Optional: Upload cookies.txt", type=["txt"])
    if st.button("Clear Results"):
        st.session_state.transcript = ""
        st.session_state.chapter = ""
        st.session_state.processed = False
        st.rerun()

# 4. TABBED INTERFACE
tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Recording"])

with tab1:
    file_vid = st.file_uploader("Choose MP4/MOV", type=["mp4", "mov"], key="file_up")
with tab2:
    url_link = st.text_input("Paste YouTube or Disney+ URL:")
with tab3:
    live_text = st.text_area("Live Commentary / Plot Tweaks:", placeholder="Make the old man scene more emotional...")

# 5. THE PRODUCTION BUTTON
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Gemini 2.5 Flash is analyzing...") as status:
        try:
            # Upload/Download Logic
            source_path = ""
            if file_vid:
                source_path = "input_vid.mp4"
                with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                # Basic download logic
                source_path = "downloaded_vid.mp4"
                cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", source_path, url_link]
                if cookie_file:
                    with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                    cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(cmd, check=True)
            
            # AI Processing
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            genai_file = genai.upload_file(path=source_path)
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"""
            Cast: {cast_info}. Notes: {live_text}.
            TASK 1: FULL TRANSCRIPT.
            ---SPLIT---
            TASK 2: 2500-word novel chapter from {pov_choice}'s POV.
            """
            
            response = model.generate_content([genai_file, prompt])
            
            # --- THE FIX: STORE IN SESSION STATE ---
            if "---SPLIT---" in response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0]
                st.session_state.chapter = parts[1]
                st.session_state.processed = True
            
            status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Error: {e}")

# 6. RESULTS DISPLAY (This now stays visible)
if st.session_state.processed:
    st.divider()
    st.balloons()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("💾 Save Transcript (.docx)", 
                           create_docx("Transcript", st.session_state.transcript), 
                           "Transcript.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.transcript, height=300)

    with col2:
        st.subheader("📖 Novel Chapter")
        st.download_button("💾 Save Novel (.docx)", 
                           create_docx("Novel", st.session_state.chapter), 
                           "Novel.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.chapter, height=300)
