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
# Using your provided key with corrected formatting
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "AIzaSyDkpF4EvYNYFNe5q0UTA1_0NBE3YykfhSY"

genai.configure(api_key=api_key)

# PERSISTENCE
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
    if st.button("🗑️ Clear All Results"):
        for key in ["transcript", "chapter", "processed"]: st.session_state[key] = "" if key != "processed" else False
        st.rerun()

# 4. TABBED INTERFACE
tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Recording"])

with tab1:
    file_vid = st.file_uploader("Choose Video", type=["mp4", "mov"])
with tab2:
    url_link = st.text_input("Paste Video URL:")
with tab3:
    live_text = st.text_area("Live Author Notes:", placeholder="Focus on Roman's reaction to the baby spell...")

# 5. THE PRODUCTION BUTTON
if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.warning("Provide a video source first!")
    else:
        with st.status("🎬 Production in progress...") as status:
            try:
                source_path = "temp_video.mp4"
                if file_vid:
                    with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
                elif url_link:
                    subprocess.run(["yt-dlp", "-f", "mp4", "-o", source_path, url_link], check=True)
                
                # --- MODEL ENGINE FIX ---
                # 'gemini-1.5-flash' is the correct identifier for the Flash model in v1/v1beta
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Upload to Google's temporary storage
                genai_file = genai.upload_file(path=source_path)
                
                # Wait for processing
                while genai_file.state.name == "PROCESSING":
                    time.sleep(3)
                    genai_file = genai.get_file(genai_file.name)

                prompt = f"""
                Roles: {cast_info}. Narrator: {pov_choice}. Notes: {live_text}.
                
                TASK 1: FULL VERBATIM TRANSCRIPT.
                ---SPLIT---
                TASK 2: 2500-word novel chapter. Giada=Mother.
                """
                
                # Use generate_content with the file object
                response = model.generate_content([genai_file, prompt])
                
                if "---SPLIT---" in response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0].strip(), parts[1].strip()
                else:
                    st.session_state.chapter = response.text
                
                st.session_state.processed = True
                status.update(label="✅ Success!", state="complete")
                st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {e}. Try refreshing the page.")

# 6. RESULTS
if st.session_state.processed:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Save Transcript", create_docx("Transcript", st.session_state.transcript), "Transcript.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.transcript, height=300)
    with c2:
        st.subheader("📖 Novel")
        st.download_button("📥 Save Novel", create_docx("Novel", st.session_state.chapter), "Novel.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.chapter, height=300)
