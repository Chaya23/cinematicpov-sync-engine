import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import subprocess
import os
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
api_key = st.secrets.get("GEMINI_API_KEY", "")
api_key = api_key.strip() if api_key else ""
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

# PERSISTENCE
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "chapter" not in st.session_state:
    st.session_state.chapter = ""
if "processed" not in st.session_state:
    st.session_state.processed = False

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()

# 2. SIDEBAR: PRODUCTION BIBLE & AGGRESSIVE SETTINGS
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area(
        "Cast Roles (Editable):",
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother"
    )
    
    st.header("👤 POV Settings")
    pov_choice = st.selectbox(
        "Narrator POV:",
        ["Roman Russo", "Billie", "Justin", "Giada", "Custom"]
    )
    if pov_choice == "Custom":
        pov_choice = st.text_input("Enter Custom Name:", value="Custom Narrator")

    st.header("🌐 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt (For Disney/Region bypass)", type=["txt"])
    geo_bypass = st.checkbox("Force Geo-Bypass (US)", value=True)

    st.divider()
    if st.button("🗑️ Reset Studio"):
        st.session_state.transcript = ""
        st.session_state.chapter = ""
        st.session_state.processed = False
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
    if not file_vid and not url_link:
        st.error("Please upload a video file or provide a URL before starting production.")
    else:
        with st.status("🎬 Aggressive Bypass & Processing...") as status:
            try:
                # DYNAMIC MODEL RESOLVER
                available_models = [
                    m.name
                    for m in genai.list_models()
                    if hasattr(m, "supported_generation_methods")
                    and "generateContent" in m.supported_generation_methods
                ]
                flash_models = [m for m in available_models if "flash" in m.lower()]
                selected_model = flash_models[0] if flash_models else "models/gemini-1.5-flash"

                # STORAGE CLEANUP (ignore failures silently)
                try:
                    for f in genai.list_files():
                        genai.delete_file(f.name)
                except Exception:
                    pass

                source = "temp_video.mp4"

                # --- AGGRESSIVE DOWNLOAD LOGIC ---
                if file_vid:
                    with open(source, "wb") as f:
                        f.write(file_vid.getbuffer())
                elif url_link:
                    ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", source]
                    if geo_bypass:
                        ydl_cmd.extend(["--geo-bypass", "--geo-bypass-country", "US"])
                    if cookie_file:
                        with open("cookies.txt", "wb") as f:
                            f.write(cookie_file.getbuffer())
                        ydl_cmd.extend(["--cookies", "cookies.txt"])
                    ydl_cmd.append(url_link)
                    subprocess.run(ydl_cmd, check=True)

                # --- AI PROCESSING ---
                safety_settings = [
                    {
                        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                        "threshold": HarmBlockThreshold.BLOCK_NONE,
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        "threshold": HarmBlockThreshold.BLOCK_NONE,
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        "threshold": HarmBlockThreshold.BLOCK_NONE,
                    },
                    {
                        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        "threshold": HarmBlockThreshold.BLOCK_NONE,
                    },
                ]

                model = genai.GenerativeModel(selected_model)
                genai_file = genai.upload_file(path=source)

                while getattr(genai_file, "state", None) and genai_file.state.name == "PROCESSING":
                    time.sleep(5)
                    genai_file = genai.get_file(genai_file.name)

                prompt = f"""
                Cast: {cast_info}. Narrator: {pov_choice}. Notes: {live_notes}.
                TASK 1: FULL VERBATIM TRANSCRIPT. 
                ---SPLIT---
                TASK 2: 2500-word novel chapter from {pov_choice}'s POV. 
                Detailed internal monologue. Giada is mother.
                """

                response = model.generate_content(
                    [genai_file, prompt],
                    safety_settings=safety_settings,
                )

                if getattr(response, "candidates", None):
                    full_text = response.text or ""
                    if "---SPLIT---" in full_text:
                        parts = full_text.split("---SPLIT---", 1)
                        st.session_state.transcript = parts[0].strip()
                        st.session_state.chapter = parts[1].strip()
                    else:
                        st.session_state.transcript = ""
                        st.session_state.chapter = full_text.strip()
                    st.session_state.processed = True
                    st.rerun()
                else:
                    st.error(
                        "AI blocked or returned empty content. "
                        "This sometimes happens with URL metadata. Try using 'File Upload'."
                    )

            except subprocess.CalledProcessError as e:
                st.error(f"Download error (yt-dlp): {e}")
            except Exception as e:
                st.error(f"Error: {e}")

# 5. RESULTS HUB
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.text_area("T-Preview", st.session_state.transcript, height=450)
        st.download_button(
            "📥 Save Transcript",
            create_docx("Transcript", st.session_state.transcript),
            "Transcript.docx",
        )

    with col2:
        st.subheader(f"📖 Novel: {pov_choice} POV")
        st.text_area("N-Preview", st.session_state.chapter, height=450)
        st.download_button(
            "📥 Save Novel",
            create_docx(f"{pov_choice} Chapter", st.session_state.chapter),
            "Novel.docx",
        )
