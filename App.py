import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import subprocess
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# 1. SECURE KEY & SAFETY CONFIG
raw_key = st.secrets.get("GEMINI_API_KEY", "")
if raw_key:
    genai.configure(api_key=raw_key.strip())
else:
    st.error("🔑 Key not found in Secrets!")
    st.stop()

# --- THE FIX: SAFETY OVERRIDE ---
# This prevents the "Response.parts is empty" error by disabling the blocks
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# 2. STATE & EXPORTER
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 3. UI
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast:", "Giada: Mother\nJustin: Father\nRoman: Protagonist")
    pov_choice = st.selectbox("Narrator:", ["Roman Russo", "Billie", "Justin"])

t_up, t_url = st.tabs(["📁 File Upload", "🌐 URL Sync"])
with t_up:
    file_vid = st.file_uploader("Upload MP4", type=["mp4"])
with t_url:
    url_link = st.text_input("Paste Video URL")

# 4. PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Processing... (Overriding Safety Filters)") as status:
        try:
            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            genai_file = genai.upload_file(path=source)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            prompt = f"Cast: {cast_info}. Narrator: {pov_choice}. TASK 1: VERBATIM TRANSCRIPT. ---SPLIT--- TASK 2: 2500-word chapter."
            
            # --- THE FIX: PASS SAFETY SETTINGS HERE ---
            response = model.generate_content(
                [genai_file, prompt],
                safety_settings=safety_settings
            )
            
            # Check if response actually exists before accessing parts
            if response.candidates:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript, st.session_state.chapter = parts[0].strip(), parts[1].strip()
                else:
                    st.session_state.chapter = full_text
                status.update(label="✅ Success!", state="complete")
                st.rerun()
            else:
                st.error(f"AI Blocked: {response.prompt_feedback}")
                
        except Exception as e:
            st.error(f"Error: {e}")

# 5. RESULTS
if st.session_state.chapter:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📜 Transcript")
        st.download_button("📥 Save Transcript", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
        st.text_area("T-Preview", st.session_state.transcript, height=250)
    with c2:
        st.subheader("📖 Novel")
        st.download_button("📥 Save Novel", create_docx("Novel", st.session_state.chapter), "Novel.docx")
        st.text_area("N-Preview", st.session_state.chapter, height=250)
