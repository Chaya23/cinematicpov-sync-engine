import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. CONFIG & API ----------------

st.set_page_config(page_title="Cinematic POV Story Engine", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing. Add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# Initialize Session State
for key, default in [
    ("transcript", ""),
    ("chapter", ""),
    ("processed", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------- 2. HELPERS ----------------

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def get_safety_settings():
    return {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

def clean_cloud_storage():
    try:
        for f in genai.list_files():
            genai.delete_file(f.name)
    except:
        pass

# ---------------- 3. SIDEBAR (The Bible) ----------------

with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast List (name: role):", 
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother\nBillie: Sister", 
        height=150)
    
    st.header("👤 POV Settings")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Billie", "Justin", "Giada", "Custom"])
    if pov_choice == "Custom":
        pov_choice = st.text_input("Custom Name:", "Narrator")

    st.header("🌐 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt (For DisneyNow/DRM)", type=["txt"])
    
    if st.button("🗑️ Reset Studio"):
        st.session_state.clear()
        st.rerun()

# ---------------- 4. MAIN INTERFACE ----------------

st.title("🎬 Cinematic POV Story Engine")

tab_up, tab_url = st.tabs(["📁 File Upload (Reliable)", "🌐 URL Sync (Aggressive)"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4 Video", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Video URL (DisneyNow, YouTube):")
    st.caption("⚠️ Use cookies.txt in the sidebar for protected sites.")

# ---------------- 5. PRODUCTION ENGINE ----------------

if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.error("Please provide a video file or a URL.")
    else:
        with st.status("🎬 Running Production Pipeline...") as status:
            try:
                # Resolve Model
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                selected_model = [m for m in available if 'flash' in m.lower()][0] or "models/gemini-1.5-flash"
                
                # Cleanup & Save
                clean_cloud_storage()
                source = "temp_video.mp4" # FORCING EXTENSION FOR GEMINI

                if file_vid:
                    with open(source, "wb") as f:
                        f.write(file_vid.getbuffer())
                elif url_link:
                    ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", source]
                    if cookie_file:
                        with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                        ydl_cmd.extend(["--cookies", "cookies.txt"])
                    subprocess.run(ydl_cmd, check=True)

                # Upload to Gemini
                status.update(label="📤 Uploading to AI...", state="running")
                gem_file = genai.upload_file(path=source)
                while gem_file.state.name == "PROCESSING":
                    time.sleep(4)
                    gem_file = genai.get_file(gem_file.name)

                # Generate Content
                status.update(label="🧠 Writing Transcript & Novel...", state="running")
                model = genai.GenerativeModel(selected_model)
                prompt = f"""
                CAST: {cast_info}
                POV: {pov_choice}
                
                TASK 1: Full verbatim transcript.
                ---SPLIT---
                TASK 2: 2500-word novel chapter in FIRST PERSON from {pov_choice}. 
                Focus on internal monologue and sensory details. Giada is mother.
                """
                
                response = model.generate_content([gem_file, prompt], safety_settings=get_safety_settings())

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
                    st.error("AI Blocked the content. Try a shorter file upload.")

            except Exception as e:
                st.error(f"Studio Error: {e}")

# ---------------- 6. RESULTS ----------------

if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.text_area("T-Preview", st.session_state.transcript, height=400)
        st.download_button("📥 Save Transcript", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
    with col2:
        st.subheader(f"📖 Novel ({pov_choice})")
        st.text_area("N-Preview", st.session_state.chapter, height=400)
        st.download_button("📥 Save Novel", create_docx("Novel", st.session_state.chapter), "Novel.docx")
