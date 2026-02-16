import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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
    st.error("🔑 API Key missing from Streamlit Secrets.")
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

# 2. SIDEBAR: PRODUCTION BIBLE & POV
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast Roles (Editable):", 
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother")
    
    st.header("👤 POV Settings")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Billie", "Justin", "Giada", "Custom"])
    if pov_choice == "Custom":
        pov_choice = st.text_input("Enter Custom Name:")

    st.divider()
    if st.button("🗑️ Reset Studio"):
        for key in ["transcript", "chapter", "processed"]: st.session_state[key] = "" if key != "processed" else False
        st.rerun()

# 3. TABS: INPUT METHODS
tab_up, tab_url, tab_live = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Notes"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste DisneyNow/YouTube URL:")
with tab_live:
    live_notes = st.text_area("Live Production Notes:", placeholder="Add plot twists here...")

# 4. PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Resolving Model & Bypassing Filters...") as status:
        try:
            # --- THE 404 FIX: DYNAMIC MODEL RESOLVER ---
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Priority: Look for 1.5 Flash, then any Flash model
            flash_models = [m for m in available_models if 'flash' in m.lower()]
            selected_model = flash_models[0] if flash_models else "models/gemini-1.5-flash"
            
            # --- STORAGE CLEANUP ---
            for f in genai.list_files(): genai.delete_file(f.name)

            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            # --- SAFETY OVERRIDE ---
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            model = genai.GenerativeModel(selected_model)
            genai_file = genai.upload_file(path=source)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"""
            Cast: {cast_info}. Narrator: {pov_choice}. Notes: {live_notes}.
            TASK 1: FULL VERBATIM TRANSCRIPT.
            ---SPLIT---
            TASK 2: 2500-word novel chapter from {pov_choice}'s POV. 
            Focus on internal monologue and Roman's development.
            """
            
            response = model.generate_content([genai_file, prompt], safety_settings=safety_settings)
            
            if response.candidates:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0], parts[1]
                else:
                    st.session_state.chapter = full_text
                st.session_state.processed = True
                st.rerun()
            else:
                st.error("AI blocked content. Try uploading a local file to bypass URL restrictions.")

        except Exception as e:
            st.error(f"Error: {e}")

# 5. RESULTS HUB (Two Columns)
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.text_area("T-Preview", st.session_state.transcript, height=450)
        st.download_button("📥 Save Transcript (.docx)", 
                           create_docx("Transcript", st.session_state.transcript), 
                           "Transcript.docx")

    with col2:
        st.subheader(f"📖 Novel: {pov_choice} POV")
        st.text_area("N-Preview", st.session_state.chapter, height=450)
        st.download_button("📥 Save Novel (.docx)", 
                           create_docx(f"{pov_choice} Chapter", st.session_state.chapter), 
                           "Novel.docx")
