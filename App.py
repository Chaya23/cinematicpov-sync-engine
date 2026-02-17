import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. SETUP & CONFIG ----------------
st.set_page_config(page_title="Fanfic POV Engine", layout="wide")

# API Key Check
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing. Please add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# --- NEW: AUTO-MODEL DISCOVERY ---
def get_best_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioritize Flash models for video processing
        flash_models = [m for m in models if "flash" in m.lower()]
        if flash_models:
            return flash_models[0] # Returns 'models/gemini-1.5-flash' or similar
        return models[0]
    except Exception as e:
        st.error(f"Could not list models: {e}")
        return "models/gemini-1.5-flash" # Fallback

# Persistent State
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

# ---------------- 2. SIDEBAR ----------------
with st.sidebar:
    st.header("🎭 Character Bible")
    default_cast = "Roman: Protagonist\nGiada: Mother\nJustin: Father\nBillie: Sister\nMilo: Brother\nWinter: Friend\nSuperintendent Kowalski: Principal"
    cast_info = st.text_area("Cast List (name: role):", default_cast, height=200)
    
    cast_names = [line.split(":")[0].strip() for line in cast_info.split("\n") if ":" in line]
    pov_choice = st.selectbox("Narrator POV:", ["Roman"] + [n for n in cast_names if n != "Roman"])

    st.header("🍪 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt", type=["txt"])
    
    st.divider()
    if st.button("🗑️ Reset Studio"):
        st.session_state.clear()
        st.rerun()

# ---------------- 3. MAIN INTERFACE ----------------
st.title("📚 Fanfic POV Engine")
st.caption("Generate scripts and novel chapters from any video")

tab_up, tab_url = st.tabs(["📁 Local Video Upload", "🌐 Streaming URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Video URL:")

# ---------------- 4. PRODUCTION ENGINE ----------------
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status(f"🎬 Processing via {pov_choice}'s perspective...") as status:
        source = "temp_video.mp4"
        try:
            # 4.1. Extraction Logic
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                status.update(label="⬇️ Downloading...", state="running")
                ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "--geo-bypass", "-o", source]
                if cookie_file:
                    with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                    ydl_cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(ydl_cmd, check=True)

            # 4.2. Gemini Upload
            status.update(label="📤 Uploading for AI Analysis...", state="running")
            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            # 4.3. DYNAMIC MODEL SELECTION
            active_model = get_best_model()
            st.info(f"Using Model: {active_model}")
            model = genai.GenerativeModel(active_model)
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            # 4.4. Unified Fanfic Prompt
            prompt = f"""
            Identify characters via visual/audio grounding. POV: {pov_choice}.
            CAST BIBLE: {cast_info}

            TASK 1: FULL TRANSCRIPT
            - Accurately tag speakers by name.
            - Include important actions in [brackets].
            
            ---SPLIT---

            TASK 2: FIRST-PERSON NOVEL CHAPTER
            - Narrator: {pov_choice}.
            - Write in a descriptive, emotional style.
            - Focus on {pov_choice}'s internal feelings about the events in the video.
            """

            # 4.5. Generation
            status.update(label="🧠 Writing Fanfic Content...", state="running")
            response = model.generate_content([gem_file, prompt], safety_settings=safety_settings)

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip() if len(parts) > 0 else ""
                st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                st.rerun()

        except Exception as e:
            st.error(f"Studio Error: {e}")
        finally:
            if os.path.exists(source): os.remove(source)
            if os.path.exists("cookies.txt"): os.remove("cookies.txt")

# ---------------- 5. RESULTS ----------------
if st.session_state.transcript or st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Speaker Transcript")
        st.text_area("T-Box", st.session_state.transcript, height=550)
    with col2:
        st.subheader(f"📖 {pov_choice}'s Novel POV")
        st.text_area("N-Box", st.session_state.chapter, height=550)
