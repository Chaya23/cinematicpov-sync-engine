import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. SETUP ----------------
st.set_page_config(page_title="Fanfic POV Engine", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 Add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split("\n"):
        doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ---------------- 2. SIDEBAR (Sitcom Logic) ----------------
with st.sidebar:
    st.header("🎭 Sitcom Character Bible")
    st.info("Sitcoms use 'blocking'. Tell the AI who usually stands where.")
    visual_cues = (
        "Roman: Smallest boy, anxious, often wearing layers or 'pillow armor'.\n"
        "Billie: Rebellious girl, colorful hair, taller than Roman.\n"
        "Justin: Tall adult male, 'Dad' energy.\n"
        "Milo: Younger brother, often holding props or animals."
    )
    cast_info = st.text_area("Visual Cues:", visual_cues, height=180)
    pov_choice = st.selectbox("Narrator POV:", ["Roman", "Billie", "Milo", "Justin"])

# ---------------- 3. PRODUCTION ----------------
st.title("📚 Fanfic POV Engine")
st.caption("Optimized for Multi-Camera Sitcom Continuity")

file_vid = st.file_uploader("Upload Episode", type=["mp4", "mov"])

if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Analyzing Sitcom Blocking...") as status:
        source = "temp_video.mp4"
        try:
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
                
                status.update(label="📤 Uploading for Spatial Analysis...", state="running")
                gem_file = genai.upload_file(path=source)
                while gem_file.state.name == "PROCESSING":
                    time.sleep(2)
                    gem_file = genai.get_file(gem_file.name)

                # Use the latest model that worked for you on mobile
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # SITCOM-SPECIFIC PROMPT
                prompt = f"""
                You are analyzing a MULTI-CAMERA SITCOM. 
                SITCOM RULES: The camera cuts between wide 'master' shots and close-ups. 
                Track characters based on their 'blocking' (position on stage) and clothing.
                
                CHARACTERS: {cast_info}
                IMPORTANT: Billie is a teen girl. Roman is a younger boy. Do not swap their names.

                TASK 1: FULL TRANSCRIPT
                - Format as [Name]: [Dialogue]
                - Include [Audience Laughter] and [Physical Comedy Actions].
                
                ---SPLIT---

                TASK 2: FIRST-PERSON NOVEL CHAPTER
                - POV: {pov_choice}
                - Style: Young Adult Fiction. 
                - Translate the sitcom 'jokes' into {pov_choice}'s internal monologue. 
                - Make it feel like a real book, not a script.
                """
                
                response = model.generate_content([gem_file, prompt])
                
                if response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if os.path.exists(source): os.remove(source)

# ---------------- 4. DISPLAY ----------------
if "transcript" in st.session_state and st.session_state.transcript:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Sitcom Transcript")
        st.download_button("📥 Save Transcript (Word)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
        st.text_area("T-Box", st.session_state.transcript, height=500)

    with col2:
        st.subheader(f"📖 {pov_choice}'s Internal Monologue")
        st.download_button("📥 Save Novel (Word)", create_docx("Novel Chapter", st.session_state.chapter), "Novel.docx")
        st.text_area("N-Box", st.session_state.chapter, height=500)
