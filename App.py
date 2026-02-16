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
# Using your provided key - cleaned of extra spaces
api_key = st.secrets.get("GEMINI_API_KEY", "AIzaSyDkpF4EvYNYFNe5q0UTA1_0NBE3YykfhSY")
genai.configure(api_key=api_key)

# PERSISTENCE (Crucial for Mobile)
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""
if "processed" not in st.session_state: st.session_state.processed = False

# 2. SEPARATE WORD EXPORTERS
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
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother\nBillie: Sister")
    pov_choice = st.selectbox("Novel Narrator:", ["Roman Russo", "Billie", "Justin"])
    if st.button("🗑️ Reset Studio"):
        for k in ["transcript", "chapter", "processed"]: st.session_state[k] = "" if k != "processed" else False
        st.rerun()

# 4. TABBED INTERFACE (Separate Tabs for URL and Upload)
tab_up, tab_url, tab_live = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Recording"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Video Link (YouTube/DisneyNow):")
with tab_live:
    live_text = st.text_area("Live Author Notes:", placeholder="Add plot twists here...")

# 5. THE PRODUCTION BUTTON
if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.warning("Please provide a video source!")
    else:
        with st.status("🎬 Processing... This takes 1-2 mins for 23min videos") as status:
            try:
                source_path = "temp_video.mp4"
                if file_vid:
                    with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
                elif url_link:
                    # Best mp4 format for Gemini compatibility
                    subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source_path, url_link], check=True)
                
                # --- FIXED MODEL NAME ---
                # We use the stable 1.5-flash for API video processing
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Upload to Google's Temporary Cloud Storage
                genai_file = genai.upload_file(path=source_path)
                
                # Wait for Google to index the video
                while genai_file.state.name == "PROCESSING":
                    time.sleep(4)
                    genai_file = genai.get_file(genai_file.name)

                prompt = f"""
                You are a master scriptwriter.
                Cast: {cast_info}. Notes: {live_text}.
                
                TASK 1: Generate a FULL VERBATIM TRANSCRIPT.
                ---SPLIT---
                TASK 2: Write a 2500-word novel chapter from {pov_choice}'s POV. 
                Focus on Roman's growth. Giada is the mother.
                """
                
                response = model.generate_content([genai_file, prompt])
                
                # SEPARATE THE RESULTS
                if "---SPLIT---" in response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.chapter = parts[1].strip()
                else:
                    st.session_state.chapter = response.text
                
                st.session_state.processed = True
                status.update(label="✅ Production Complete!", state="complete")
                st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {e}. Check your Internet and API Quota.")

# 6. RESULTS HUB (Separate Exports)
if st.session_state.processed:
    st.divider()
    st.balloons()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Download Transcript (.docx)", 
                           create_docx("Verbatim Transcript", st.session_state.transcript), 
                           "Transcript.docx", use_container_width=True)
        st.text_area("Transcript Preview", st.session_state.transcript, height=300)

    with col2:
        st.subheader("📖 Novel Chapter")
        st.download_button("📥 Download Novel (.docx)", 
                           create_docx(f"{pov_choice} POV Chapter", st.session_state.chapter), 
                           "Novel.docx", use_container_width=True)
        st.text_area("Novel Preview", st.session_state.chapter, height=300)
