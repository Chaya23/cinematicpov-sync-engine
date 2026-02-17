import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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
    st.header("🎭 Custom Cast List")
    cast_info = st.text_area("Cast (name: role):", 
        "Roman: Protagonist/Narrator\nGiada: Mother\nJustin: Father\nBillie: Sister\nTheresa: Grandmother", height=150)
    
    st.header("⚙️ Studio Reset")
    if st.button("🗑️ Clear All"):
        st.session_state.clear()
        st.rerun()

# 3. INPUT
st.title("🎬 Cinematic POV Story Engine")
tab_up, tab_url = st.tabs(["📁 Video Upload", "🌐 YouTube / Disney URL"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste URL:")
    cookie_file = st.file_uploader("Upload cookies.txt (for DisneyNow)", type=["txt"])

# 4. PRODUCTION
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Grounding Roman's Perspective...") as status:
        try:
            # Cleanup
            for f in genai.list_files(): genai.delete_file(f.name)

            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", source]
                if cookie_file:
                    with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                    ydl_cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(ydl_cmd, check=True)

            # Upload
            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            # --- ROMAN-CENTRIC PROMPT ---
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Analyze this video strictly through the eyes of the protagonist: Roman.
            
            CAST:
            {cast_info}
            
            TASK 1: VERBATIM TRANSCRIPT
            - Identify Roman's Dialogue vs. Roman's Voiceover (Narration).
            - Identify other characters speaking.
            - Ensure speaker tags are 100% accurate using visual grounding.
            
            ---SPLIT---
            
            TASK 2: FIRST-PERSON NOVEL CHAPTER
            - POV: Roman Russo.
            - Focus: Roman's internal monologue, his feelings, and his unique perspective.
            - LIMITATION: If Roman is NOT in a scene, write about how he "heard about it later" or what he "discovered happened" after the fact. Do not describe scenes he didn't witness as if he were there.
            - STYLE: YA Novel, deep sensory detail, roughly 2500 words.
            """
            
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in HarmCategory}
            response = model.generate_content([gem_file, prompt], safety_settings=safety)

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip() if len(parts) > 0 else ""
                st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")

# 5. BOXES & EXPORTS
if st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.download_button("📥 Save Transcript (.docx)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
        st.text_area("T-Box", st.session_state.transcript, height=500)
    with col2:
        st.subheader("📖 Roman's Perspective")
        st.download_button("📥 Save Novel (.docx)", create_docx("Roman's Chapter", st.session_state.chapter), "Novel.docx")
        st.text_area("N-Box", st.session_state.chapter, height=500)
