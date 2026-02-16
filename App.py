import streamlit as st
import google.generativeai as genai
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# --- SECURE API CONNECTION ---
# This looks for the key in your "Secrets" dashboard, NOT in the code.
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🔑 SECURITY ERROR: API Key not found in Secrets. Please add GEMINI_API_KEY to your Streamlit dashboard.")
    st.stop()

# PERSISTENCE
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""
if "processed" not in st.session_state: st.session_state.processed = False

# 2. SEPARATE WORD EXPORTS
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 3. SIDEBAR & CAST
with st.sidebar:
    st.header("⚙️ Studio Settings")
    cast_info = st.text_area("Cast Roles:", "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother")
    pov_choice = st.selectbox("Narrator:", ["Roman Russo", "Billie", "Justin"])
    if st.button("🗑️ Clear Memory"):
        st.session_state.transcript = st.session_state.chapter = ""
        st.session_state.processed = False
        st.rerun()

# 4. TABS
tab_up, tab_url, tab_live = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Recording"])

with tab_up:
    file_vid = st.file_uploader("Upload Video", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Link (YouTube/Disney):")
with tab_live:
    live_text = st.text_area("Live Notes:")

# 5. THE PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Safely processing episode...") as status:
        try:
            # AUTO-DISCOVERY OF MODELS (Prevents 404)
            models = [m.name for m in genai.list_models() if 'flash' in m.name.lower()]
            selected_model = models[0] if models else "gemini-1.5-flash"
            
            source_path = "temp_video.mp4"
            if file_vid:
                with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source_path, url_link], check=True)
            
            model = genai.GenerativeModel(selected_model)
            genai_file = genai.upload_file(path=source_path)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
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
            status.update(label="✅ Success!", state="complete")
            st.rerun()
                
        except Exception as e:
            st.error(f"Error: {e}")

# 6. RESULTS (Separate Word Files)
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Save Transcript (.docx)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.transcript, height=300)
    with col2:
        st.subheader("📖 Novel")
        st.download_button("📥 Save Novel (.docx)", create_docx("Novel", st.session_state.chapter), "Novel.docx", use_container_width=True)
        st.text_area("Preview", st.session_state.chapter, height=300)
