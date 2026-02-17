import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# 1. SETUP
st.set_page_config(page_title="Roman's POV Studio", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing.")
    st.stop()

genai.configure(api_key=api_key)

if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split("\n"):
        doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 2. SIDEBAR
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast List (name: role):", 
        "Roman: Protagonist\nGiada: Mother\nJustin: Father\nBillie: Sister", height=200)
    
    st.header("👤 POV Narrator")
    cast_names = [line.split(":")[0].strip() for line in cast_info.split("\n") if ":" in line]
    pov_choice = st.selectbox("Narrator:", ["Roman"] + [n for n in cast_names if n != "Roman"])

    st.header("🍪 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt", type=["txt"])
    
    if st.button("🗑️ Reset Studio"):
        st.session_state.clear()
        st.rerun()

# 3. MAIN INPUT
st.title("🎬 Cinematic POV Story Engine")
tab_up, tab_url = st.tabs(["📁 Local Upload", "🌐 URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Episode URL:")

# 4. PRODUCTION
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Extraction & Analysis...") as status:
        try:
            for f in genai.list_files(): genai.delete_file(f.name)

            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "--geo-bypass", "-o", source]
                if cookie_file:
                    with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                    ydl_cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(ydl_cmd, check=True)

            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            # THE FIXED SAFETY BLOCK
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
            ]

            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Identify characters via visual grounding. Narrator: {pov_choice}.
            CAST: {cast_info}
            TASK 1: VERBATIM TRANSCRIPT (Tag speakers accurately).
            ---SPLIT---
            TASK 2: 2500-WORD FIRST-PERSON NOVEL CHAPTER from POV of {pov_choice}.
            """
            
            response = model.generate_content([gem_file, prompt], safety_settings=safety_settings)

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip()
                st.session_state.chapter = parts[1].strip()
                st.rerun()

        except Exception as e:
            st.error(f"Studio Error: {e}")

# 5. BOXES
if st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Save Transcript (.docx)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
        st.text_area("T-Box", st.session_state.transcript, height=500)
    with col2:
        st.subheader(f"📖 {pov_choice}'s Chapter")
        st.download_button("📥 Save Novel (.docx)", create_docx("Novel", st.session_state.chapter), "Novel.docx")
        st.text_area("N-Box", st.session_state.chapter, height=500)
