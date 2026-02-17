import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. SETUP & CONFIG ----------------
st.set_page_config(page_title="Roman's POV Story Engine", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# Persistent State for Results
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

# ---------------- 2. SIDEBAR (Cast & POV Control) ----------------
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast List (name: role):", 
        "Roman: Protagonist/Narrator\nGiada: Mother\nJustin: Father\nBillie: Sister\nTheresa: Grandmother", height=200)
    
    # Extract names for the POV dropdown automatically
    cast_names = [line.split(":")[0].strip() for line in cast_info.split("\n") if ":" in line]
    
    st.header("👤 Narrator Settings")
    pov_choice = st.selectbox("Current POV Narrator:", ["Roman"] + [name for name in cast_names if name != "Roman"] + ["Custom"])
    if pov_choice == "Custom":
        pov_choice = st.text_input("Enter Custom POV Name:")

    st.divider()
    if st.button("🗑️ Clear All & Reset Studio"):
        st.session_state.clear()
        st.rerun()

# ---------------- 3. INPUT (Files & URLs) ----------------
st.title("🎬 Cinematic POV Story Engine")

tab_up, tab_url = st.tabs(["📁 Local Video Upload", "🌐 Streaming URL (Disney+/YouTube)"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste URL (DisneyNow, YouTube, etc.):")
    cookie_file = st.file_uploader("Upload cookies.txt (Bypass Disney DRM)", type=["txt"])

# ---------------- 4. PRODUCTION ENGINE ----------------
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status(f"🎬 Processing through {pov_choice}'s perspective...") as status:
        try:
            # Storage Cleanup
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

            # AI Process
            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Analyze this video strictly from the perspective of {pov_choice}.
            
            CAST BIBLE:
            {cast_info}
            
            TASK 1: VERBATIM TRANSCRIPT
            - Differentiate between Dialogue and Voiceover (VO).
            - Use visual grounding to ensure speaker tags match the cast bible.
            - Ensure speaker identification is 100% accurate.
            
            ---SPLIT---
            
            TASK 2: FIRST-PERSON NOVEL CHAPTER
            - Narrator: {pov_choice}.
            - Focus: Internal monologue, personal stakes, and the narrator's unique feelings.
            - AUTHENTICITY RULE: If {pov_choice} isn't in a scene, they must "hear about it" or "see the aftermath." No third-person "god-view."
            - Length: Approx 2500 words, YA Novel style.
            """
            
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in HarmCategory}
            response = model.generate_content([gem_file, prompt], safety_settings=safety)

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip() if len(parts) > 0 else ""
                st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                st.rerun()

        except Exception as e:
            st.error(f"Studio Error: {e}")

# ---------------- 5. SEPARATE RESULT BOXES ----------------
if st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.download_button("📥 Export Transcript (Word)", 
                           create_docx("Verbatim Transcript", st.session_state.transcript), 
                           "Transcript.docx")
        st.text_area("Transcript Preview", st.session_state.transcript, height=550)
        
    with col2:
        st.subheader(f"📖 {pov_choice}'s Novel Chapter")
        st.download_button("📥 Export Novel (Word)", 
                           create_docx(f"{pov_choice} POV Chapter", st.session_state.chapter), 
                           "Novel.docx")
        st.text_area("Novel Preview", st.session_state.chapter, height=550)
