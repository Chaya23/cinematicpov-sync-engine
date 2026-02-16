import streamlit as st
import google.generativeai as genai
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

# PERSISTENCE
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""
if "processed" not in st.session_state: st.session_state.processed = False

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 2. SIDEBAR: THE PRODUCTION BIBLE
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast Roles:", "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother")
    
    st.header("👤 POV Settings")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Billie", "Justin", "Giada"])
    
    st.divider()
    if st.button("🗑️ Reset Studio"):
        for key in ["transcript", "chapter", "processed"]: st.session_state[key] = "" if key != "processed" else False
        st.rerun()

# 3. TABS: INPUT
tab_up, tab_url = st.tabs(["📁 File Upload", "🌐 URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4 (Highest Success Rate)", type=["mp4"])
with tab_url:
    url_link = st.text_input("Paste Video URL:", placeholder="YouTube or DisneyNow Link")

# 4. PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Processing... Overriding Safety Filters") as status:
        try:
            # CLEANUP OLD FILES
            for f in genai.list_files(): genai.delete_file(f.name)

            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            # MODEL & SAFETY SETUP
            # We use gemini-1.5-flash which is standard for video
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # BROADEST SAFETY SETTINGS POSSIBLE
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            genai_file = genai.upload_file(path=source)
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"""
            CAST: {cast_info}. 
            POV: {pov_choice}.
            TASK 1: FULL VERBATIM TRANSCRIPT.
            ---SPLIT---
            TASK 2: 2500-word novel chapter based on this episode.
            """
            
            response = model.generate_content([genai_file, prompt], safety_settings=safety_settings)
            
            # VALIDATION
            if response.candidates and len(response.candidates[0].content.parts) > 0:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0], parts[1]
                else:
                    st.session_state.chapter = full_text
                st.session_state.processed = True
                st.rerun()
            else:
                st.error("AI still refusing based on safety. Trying local file upload usually bypasses URL-based copyright blocks.")

        except Exception as e:
            st.error(f"Error: {e}")

# 5. RESULTS HUB
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.text_area("T-Box", st.session_state.transcript, height=400)
        st.download_button("📥 Save Transcript", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
    with col2:
        st.subheader(f"📖 Novel ({pov_choice})")
        st.text_area("N-Box", st.session_state.chapter, height=400)
        st.download_button("📥 Save Novel", create_docx("Novel", st.session_state.chapter), "Novel.docx")
