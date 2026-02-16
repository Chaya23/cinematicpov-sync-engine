import streamlit as st
import google.generativeai as genai
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
api_key = st.secrets.get("GEMINI_API_KEY", 
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

# 3. SIDEBAR: MODEL CHECKER
with st.sidebar:
    st.header("⚙️ System Check")
    if st.button("Check Available Models"):
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.write(models)
    
    st.divider()
    cast_info = st.text_area("Cast Roles:", "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother")
    pov_choice = st.selectbox("Narrator:", ["Roman Russo", "Billie", "Justin"])

# 4. TABS
tab_up, tab_url, tab_live = st.tabs(["📁 Upload", "🌐 Link", "🎙️ Notes"])

with tab_up:
    file_vid = st.file_uploader("Upload Video", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Video Link:")
with tab_live:
    live_text = st.text_area("Live Notes:")

# 5. THE PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Finding best model and processing...") as status:
        try:
            # AUTO-SELECT THE MODEL
            # We look for the newest Flash model available to your key
            available_models = [m.name for m in genai.list_models() if 'flash' in m.name.lower()]
            # Pick the first one (usually the most compatible)
            selected_model = available_models[0] if available_models else "models/gemini-1.5-flash"
            
            source_path = "temp_video.mp4"
            if file_vid:
                with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "mp4", "-o", source_path, url_link], check=True)
            
            # INITIALIZE MODEL
            model = genai.GenerativeModel(selected_model)
            
            # UPLOAD & WAIT
            genai_file = genai.upload_file(path=source_path)
            while genai_file.state.name == "PROCESSING":
                time.sleep(4)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"""
            Cast: {cast_info}. Notes: {live_text}.
            TASK 1: FULL VERBATIM TRANSCRIPT.
            ---SPLIT---
            TASK 2: 2500-word novel chapter from {pov_choice}'s POV. 
            """
            
            response = model.generate_content([genai_file, prompt])
            
            if "---SPLIT---" in response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript, st.session_state.chapter = parts[0].strip(), parts[1].strip()
            else:
                st.session_state.chapter = response.text
            
            st.session_state.processed = True
            st.rerun()
                
        except Exception as e:
            st.error(f"Error: {e}")

# 6. RESULTS HUB
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Download (.docx)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.transcript, height=300)
    with col2:
        st.subheader("📖 Novel")
        st.download_button("📥 Download (.docx)", create_docx("Novel", st.session_state.chapter), "Novel.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.chapter, height=300)
