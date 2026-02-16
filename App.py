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

# 2. STATE PERSISTENCE
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

# 3. SIDEBAR & CAST
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast Roles:", "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Billie", "Justin"])
    if st.button("🗑️ Reset Studio"):
        st.session_state.transcript = st.session_state.chapter = ""
        st.session_state.processed = False
        st.rerun()

# 4. TABS
tab_up, tab_url = st.tabs(["📁 File Upload", "🌐 URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode (MP4)", type=["mp4"])
with tab_url:
    url_link = st.text_input("Paste Video URL (Disney/YouTube):", placeholder="https://disneynow.com/...")

# 5. PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Resolving Model & Processing...") as status:
        try:
            # --- MODEL RESOLVER FIX ---
            # We try to find the exact model string the API currently wants
            try:
                available = [m.name for m in genai.list_models() if 'flash' in m.name.lower()]
                selected_model = available[0] if available else "models/gemini-1.5-flash"
            except:
                selected_model = "gemini-1.5-flash" # Fallback nickname

            source = "temp_video.mp4"
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                # Note: DisneyNow has heavy DRM. This may fail if the video is encrypted.
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            # INITIALIZE
            model = genai.GenerativeModel(selected_model)
            genai_file = genai.upload_file(path=source)
            
            while genai_file.state.name == "PROCESSING":
                time.sleep(5)
                genai_file = genai.get_file(genai_file.name)

            # CLEAN SAFETY SETTINGS
            safety = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            prompt = f"""
            Cast: {cast_info}. Narrator: {pov_choice}.
            TASK 1: FULL VERBATIM TRANSCRIPT.
            ---SPLIT---
            TASK 2: 2500-word novel chapter based on the video. Focus on internal monologue.
            """
            
            response = model.generate_content([genai_file, prompt], safety_settings=safety)
            
            if response.candidates:
                full_text = response.text
                if "---SPLIT---" in full_text:
                    parts = full_text.split("---SPLIT---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.chapter = parts[1].strip()
                else:
                    st.session_state.chapter = full_text
                
                st.session_state.processed = True
                status.update(label="✅ Production Complete!", state="complete")
                st.rerun()
            else:
                st.error("AI blocked the content. Please try a local file upload.")

        except Exception as e:
            st.error(f"Error: {e}")

# 6. RESULTS HUB (Separate Boxes)
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.download_button("📥 Save Transcript (.docx)", 
                           create_docx("Transcript", st.session_state.transcript), 
                           "Transcript.docx", use_container_width=True)
        st.text_area("Transcript Preview", st.session_state.transcript, height=400)

    with col2:
        st.subheader("📖 Novel Chapter")
        st.download_button("📥 Save Novel (.docx)", 
                           create_docx("Novel Chapter", st.session_state.chapter), 
                           "Novel.docx", use_container_width=True)
        st.text_area("Novel Preview", st.session_state.chapter, height=400)
