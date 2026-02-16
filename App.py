import streamlit as st
import google.generativeai as genai
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
raw_key = st.secrets.get("GEMINI_API_KEY", "")
if raw_key:
    genai.configure(api_key=raw_key.strip())
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

# 2. THE CLEANUP ENGINE (Prevents Quota Errors)
def cleanup_old_files():
    try:
        for file in genai.list_files():
            genai.delete_file(file.name)
        return True
    except Exception:
        return False

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Storage Management")
    if st.button("🧹 Clear Google Cloud Storage"):
        if cleanup_old_files():
            st.success("20GB Storage Restored!")
        else:
            st.error("Failed to clear storage.")
    
    st.divider()
    cast_info = st.text_area("Cast:", "Giada: Mother\nJustin: Father\nRoman: Protagonist")
    pov_choice = st.selectbox("Narrator:", ["Roman Russo", "Billie", "Justin"])

# 4. PRODUCTION ENGINE
t_up, t_url = st.tabs(["📁 File Upload", "🌐 URL Sync"])
with t_up:
    file_vid = st.file_uploader("Upload MP4", type=["mp4"])
with t_url:
    url_link = st.text_input("Paste Link")

if st.button("🚀 START PRODUCTION", use_container_width=True):
    # AUTO-CLEANUP BEFORE STARTING
    cleanup_old_files()
    
    with st.status("🎬 Clearing storage and processing...") as status:
        try:
            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            # MODEL SELECTION
            model = genai.GenerativeModel('gemini-1.5-flash')
            genai_file = genai.upload_file(path=source)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"Cast: {cast_info}. Narrator: {pov_choice}. TASK 1: VERBATIM TRANSCRIPT. ---SPLIT--- TASK 2: 2500-word Novel Chapter."
            
            # Use safety override to prevent blocks
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in HarmCategory}
            
            response = model.generate_content([genai_file, prompt], safety_settings=safety)
            
            if response.candidates:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0].strip(), parts[1].strip()
                else:
                    st.session_state.chapter = full_text
                st.rerun()
            else:
                st.error("AI blocked the content. Try a shorter clip.")

        except Exception as e:
            st.error(f"Error: {e}")

# 5. RESULTS DISPLAY
if "chapter" in st.session_state and st.session_state.chapter:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📜 Transcript")
        st.text_area("T-Preview", st.session_state.get("transcript", ""), height=300)
    with c2:
        st.subheader("📖 Novel")
        st.text_area("N-Preview", st.session_state.chapter, height=300)
