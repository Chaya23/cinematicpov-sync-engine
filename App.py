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
# It's safer to use st.secrets, but I've added a fallback so it works right now.
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # Use the key you provided (I've fixed the spaces)
    api_key = "AIzaSyDkpF4EvYNYFNe5q0UTA1_0NBE3YykfhSY"

genai.configure(api_key=api_key)

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
    url_link = st.text_input("Paste URL (YouTube/DisneyNow):")
with tab3:
    live_text = st.text_area("Live Commentary:", placeholder="Describe specific scenes here...")

# 5. THE PRODUCTION BUTTON
if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.warning("Please upload a file or paste a link first!")
    else:
        with st.status("🎬 Processing with Gemini 1.5 Flash...") as status:
            try:
                source_path = "temp_video.mp4"
                if file_vid:
                    with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
                elif url_link:
                    # Download using yt-dlp
                    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", source_path, url_link]
                    subprocess.run(cmd, check=True)
                
                # --- THE MODEL FIX ---
                # Using 'gemini-1.5-flash' which is the most reliable for video
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Upload the file to Gemini's File API
                genai_file = genai.upload_file(path=source_path)
                
                # Wait for the video to be processed by Google
                while genai_file.state.name == "PROCESSING":
                    time.sleep(3)
                    genai_file = genai.get_file(genai_file.name)

                prompt = f"""
                You are a professional screenwriter and novelist.
                Cast Roles: {cast_info}.
                Additional Notes: {live_text}.
                
                TASK 1: Generate a FULL VERBATIM TRANSCRIPT of this episode.
                ---SPLIT---
                TASK 2: Write a 2500-word novel chapter from {pov_choice}'s POV. 
                Ensure Giada is the mother and Theresa is the grandmother.
                """
                
                response = model.generate_content([genai_file, prompt])
                
                if "---SPLIT---" in response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.chapter = parts[1].strip()
                    st.session_state.processed = True
                    status.update(label="✅ Success!", state="complete")
                    st.rerun()
                else:
                    # If split fails, put everything in the chapter box
                    st.session_state.chapter = response.text
                    st.session_state.processed = True
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {e}")

# 6. RESULTS DISPLAY
if st.session_state.processed:
    st.divider()
    st.balloons()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        if st.session_state.transcript:
            st.download_button("📥 Save Transcript (.docx)", 
                               create_docx("Transcript", st.session_state.transcript), 
                               "Transcript.docx", use_container_width=True)
            st.text_area("Preview", st.session_state.transcript, height=400)

    with col2:
        st.subheader("📖 Novel Chapter")
        if st.session_state.chapter:
            st.download_button("📥 Save Novel (.docx)", 
                               create_docx(f"{pov_choice} Novel", st.session_state.chapter), 
                               "Novel.docx", use_container_width=True)
            st.text_area("Preview", st.session_state.chapter, height=400)
