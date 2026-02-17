import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. SETUP & CONFIG ----------------
st.set_page_config(page_title="Roman's POV Studio", layout="wide")

# API Key Check
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing. Please add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)

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

# ---------------- 2. SIDEBAR (Cast & Cookies) ----------------
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Cast List (name: role):", 
        "Roman: Protagonist/Narrator\nGiada: Mother\nJustin: Father\nBillie: Sister\nTheresa: Grandmother\nWinter: Best Friend", height=200)
    
    cast_names = [line.split(":")[0].strip() for line in cast_info.split("\n") if ":" in line]
    pov_choice = st.selectbox("Narrator POV:", ["Roman"] + [n for n in cast_names if n != "Roman"])

    st.header("🍪 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt", type=["txt"])
    
    st.divider()
    if st.button("🗑️ Reset Studio"):
        st.session_state.clear()
        st.rerun()

# ---------------- 3. MAIN INTERFACE ----------------
st.title("🎬 Cinematic POV Story Engine")
st.caption("Now powered by Gemini 3 Flash")

tab_up, tab_url = st.tabs(["📁 Local Video Upload", "🌐 Streaming URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste URL (YouTube, DisneyNow, etc.):")

# ---------------- 4. PRODUCTION ENGINE ----------------
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status(f"🎬 Grounding through {pov_choice}'s eyes...") as status:
        source = "temp_video.mp4"
        try:
            # 4.1. Extraction Logic
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                status.update(label="⬇️ Downloading via yt-dlp...", state="running")
                ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "--geo-bypass", "-o", source]
                if cookie_file:
                    with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                    ydl_cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(ydl_cmd, check=True)

            # 4.2. Gemini Upload
            status.update(label="📤 Uploading for Visual Grounding...", state="running")
            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            # 4.3. Gemini 3 Model & Safety Logic (FIXED)
            # Using 'gemini-3-flash' to solve the 404 error
            model = genai.GenerativeModel('gemini-3-flash')
            
            # Updated safety categories for 2026 API
            safety_settings = {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUAL": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            }

            # 4.4. The POV-Focused Prompt
            prompt = f"""
            Using visual grounding from the video, perform two tasks.
            NARRATOR POV: {pov_choice}
            CAST BIBLE: {cast_info}

            TASK 1: VERBATIM TRANSCRIPT
            - High-fidelity dialogue capture.
            - Differentiate Dialogue vs Voiceover (VO).
            - Tag speakers accurately.
            
            ---SPLIT---

            TASK 2: FIRST-PERSON NOVEL CHAPTER
            - Style: Young Adult Fiction.
            - Perspective: {pov_choice}'s internal monologue.
            - Special Instruction: If {pov_choice} is Roman, emphasize his 'Pillow Armor' mentality—the feeling of being bullied, ignored by adults (Justin), and the stress of the 'Russo Curse'. 
            - Focus on sensory details: the smell of the sub shop, the weight of the wand, the fear of magic going wrong.
            """

            # 4.5. Generation
            status.update(label="🧠 Analyzing and Writing...", state="running")
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

# ---------------- 5. RESULTS & EXPORTS ----------------
if st.session_state.transcript or st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.download_button("📥 Save Transcript (.docx)", 
                           create_docx("Transcript", st.session_state.transcript), 
                           "Transcript.docx")
        st.text_area("T-Box", st.session_state.transcript, height=550)
        
    with col2:
        st.subheader(f"📖 {pov_choice}'s Novel Chapter")
        st.download_button("📥 Save Novel (.docx)", 
                           create_docx("Novel Chapter", st.session_state.chapter), 
                           "Novel.docx")
        st.text_area("N-Box", st.session_state.chapter, height=550)
