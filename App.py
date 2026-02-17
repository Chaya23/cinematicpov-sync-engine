import streamlit as st
import google.generativeai as genai
from google.generativeai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIG & MODEL ---
st.set_page_config(page_title="POV Director's Cut 2026", layout="wide", page_icon="🎬")

# The Feb 2026 High-End Model
MODEL_NAME = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. WORD EXPORT UTILITY ---
def create_docx(transcript, novel, pov, show):
    doc = Document()
    doc.add_heading(f"{show}: {pov} POV Production", 0)
    doc.add_heading('Full Verbatim Transcript', level=1)
    doc.add_paragraph(transcript)
    doc.add_page_break()
    doc.add_heading(f'Novelization: {pov} Perspective', level=1)
    doc.add_paragraph(novel)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. DVR DOWNLOADER ---
def dvr_download(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"master_rec_{ts}.mp4"
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    if cookies:
        with open("cookies.txt", "wb") as f: f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])

    with st.status("🎬 Recording Master Copy..."):
        p = subprocess.run(cmd, capture_output=True, text=True)
        return fn if p.returncode == 0 else None

# --- 4. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Studio Setup")
    show_name = st.text_input("Show Name:", "Wizards Beyond Waverly Place")
    
    cast_input = st.text_area("Cast List (Name: Role)", 
                             "Roman: Sarcastic wizard\nBillie: Rebellious lead\nJustin: Mentor\nGiada: Mom/Chef")
    cast_list = [c.split(":")[0].strip() for c in cast_input.split("\n") if ":" in c]
    pov_hero = st.selectbox("Narrator POV:", cast_list)
    
    st.divider()
    c_file = st.file_uploader("🍪 Upload cookies.txt", type="txt")

# --- 5. MAIN STUDIO ---
st.title(f"🎬 {show_name} POV Studio")
link = st.text_input(f"Paste {show_name} Link:")

if st.button("🚀 Start Production Pipeline", use_container_width=True):
    video_file = dvr_download(link, c_file)
    if video_file:
        st.session_state.library.append({"file": video_file, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 6. PRODUCTION PROCESSING ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **Episode:** {item['file']} | **POV:** {item['pov']}")
        
        if st.button(f"✨ Run High-Accuracy Analysis", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is analyzing..."):
                try:
                    # Upload video
                    gf = genai.upload_file(item['file'])
                    while gf.state.name == "PROCESSING":
                        time.sleep(2)
                        gf = genai.get_file(gf.name)
                    
                    # GOOGLE SEARCH GROUNDING TOOL
                    # This searches for recaps and wikis to fix names/plot
                    model = genai.GenerativeModel(
                        model_name=MODEL_NAME,
                        tools=[{"google_search_retrieval": {}}] 
                    )
                    
                    prompt = f"""
                    WATCH: The full video provided.
                    SEARCH: Look up the official episode recap for '{item['show']}' to verify names and plot points.
                    
                    TASK 1: FULL VERBATIM TRANSCRIPT
                    - Do not summarize. Give me every line of dialogue.
                    - Correctly identify speakers: {item['cast']}.
                    - Format this section under '[TRANSCRIPT]'.
                    
                    TASK 2: DEEP POV NOVEL
                    - Write a full chapter from {item['pov']}'s perspective.
                    - Use 'Deep POV': include internal thoughts, sensory details (smells, textures), and emotions.
                    - Format this section under '[NOVEL]'.
                    """
                    
                    response = model.generate_content([gf, prompt])
                    st.session_state[f"prod_{idx}"] = response.text
                except Exception as e:
                    st.error(f"Critical AI Error: {e}")

        # DISPLAY & EXPORT
        if f"prod_{idx}" in st.session_state:
            raw = st.session_state[f"prod_{idx}"]
            try:
                t_part = raw.split("[TRANSCRIPT]")[1].split("[NOVEL]")[0].strip()
                n_part = raw.split("[NOVEL]")[1].strip()
            except:
                t_part, n_part = raw, "Error splitting parts. Check transcript box."

            col_t, col_n = st.columns(2)
            with col_t:
                st.subheader("📜 T-Box (Verbatim)")
                st.text_area("Transcript", t_part, height=500, key=f"t_{idx}")
            with col_n:
                st.subheader(f"📖 N-Box ({item['pov']}'s POV)")
                st.text_area("Novel", n_part, height=500, key=f"n_{idx}")

            # DOWNLOAD DOCX
            docx_data = create_docx(t_part, n_part, item['pov'], item['show'])
            st.download_button(
                "📄 Export to Word Doc", 
                docx_data, 
                file_name=f"{item['show']}_Script.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
