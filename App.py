import streamlit as st
import google.generativeai as genai
import time
import subprocess
import os
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP - Use the "Secrets" tab in Streamlit to add your key as GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # Fallback for local testing - paste your key here ONLY for local use
    genai.configure(api_key="PASTE_KEY_HERE_FOR_LOCAL_ONLY")

# ENSURE SESSION STATE PERSISTS
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""
if "processed" not in st.session_state: st.session_state.processed = False

# 2. DOCUMENT EXPORTER
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
    if st.button("🗑️ Clear All Results"):
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
    if not file_vid and not url_link:
        st.warning("Please upload a file or paste a link first!")
    else:
        with st.status("🎬 Gemini 2.5 Flash is analyzing...") as status:
            try:
                source_path = "temp_video.mp4"
                if file_vid:
                    with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
                elif url_link:
                    # Download using yt-dlp
                    cmd = ["yt-dlp", "-f", "mp4", "-o", source_path, url_link]
                    subprocess.run(cmd, check=True)
                
                # AI Processing
                model = genai.GenerativeModel('models/gemini-2.0-flash-exp') # Updated to latest experimental for better output
                genai_file = genai.upload_file(path=source_path)
                
                while genai_file.state.name == "PROCESSING":
                    time.sleep(2)
                    genai_file = genai.get_file(genai_file.name)

                prompt = f"""
                You are a professional screenwriter and novelist.
                Cast Roles: {cast_info}.
                Author Notes: {live_text}.
                
                TASK 1: Generate a FULL VERBATIM TRANSCRIPT of this episode.
                ---SPLIT---
                TASK 2: Write a 2500-word novel chapter from {pov_choice}'s POV. 
                Ensure Giada is the mother. Capture deep internal emotions.
                """
                
                response = model.generate_content([genai_file, prompt])
                
                # REFINED PARSING LOGIC
                if "---SPLIT---" in response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.chapter = parts[1].strip()
                    st.session_state.processed = True
                    status.update(label="✅ Success!", state="complete")
                    st.rerun() # Force a refresh to show the results
                else:
                    st.error("The AI didn't format the response correctly. Try again!")
                    
            except Exception as e:
                st.error(f"Production Error: {e}")

# 6. RESULTS DISPLAY
if st.session_state.processed:
    st.divider()
    st.balloons()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("💾 Save Transcript (.docx)", 
                           create_docx("Transcript", st.session_state.transcript), 
                           "Transcript.docx", use_container_width=True)
        st.text_area("Transcript Preview", st.session_state.transcript, height=400)

    with col2:
        st.subheader("📖 Novel Chapter")
        st.download_button("💾 Save Novel (.docx)", 
                           create_docx(f"{pov_choice} POV Novel", st.session_state.chapter), 
                           "Novel.docx", use_container_width=True)
        st.text_area("Chapter Preview", st.session_state.chapter, height=400)
