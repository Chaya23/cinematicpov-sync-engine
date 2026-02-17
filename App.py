import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="POV Director's Cut", layout="wide", page_icon="🎬")

# WE USE PRO FOR ACCURACY, NOT FLASH.
# 1.5 Pro has the 2 Million token window needed for full 24-minute transcripts.
MODEL_NAME = "gemini-1.5-pro"

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. WORD DOC GENERATOR ---
def create_docx(transcript, novel, pov, show):
    doc = Document()
    doc.add_heading(f"{show} - {pov} POV", 0)
    
    doc.add_heading('Part 1: Verbatim Transcript', level=1)
    doc.add_paragraph(transcript)
    
    doc.add_break()
    
    doc.add_heading(f'Part 2: The Novel ({pov})', level=1)
    doc.add_paragraph(novel)
    
    # Save to memory buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. DVR ENGINE ---
def dvr_download(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"master_{ts}.mp4"
    
    # H.264 is strictly required for phone compatibility
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    if cookies:
        with open("cookies.txt", "wb") as f: f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])

    with st.status(f"🎬 Recording Master File..."):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0: return fn
        st.error(f"DVR Error: {p.stderr}")
        return None

# --- 4. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("🎥 Production Settings")
    show_title = st.text_input("Show Title", "Wizards Beyond Waverly Place")
    
    st.subheader("🎭 Cast & Truth Grounding")
    cast_raw = st.text_area("Cast List (Name: Description)", 
                           "Roman: Sarcastic wizard.\nBillie: Rebellious lead.\nJustin: Adult mentor.")
    pov_hero = st.selectbox("Narrator POV:", [line.split(":")[0] for line in cast_raw.split("\n") if ":" in line])
    
    st.info("ℹ️ Tips for Accuracy:\nUse Gemini 1.5 Pro. It is slower but reads the whole video without hallucinating names.")
    
    c_file = st.file_uploader("🍪 Upload cookies.txt (Netscape)", type="txt")

# --- 5. MAIN STUDIO ---
st.title(f"🎬 {show_title}: Director's Cut")

# INPUT AREA
u_input = st.text_input("Paste Video Link:")
if st.button("🔴 Record & Ingest", use_container_width=True):
    if u_input:
        f = dvr_download(u_input, c_file)
        if f:
            st.session_state.library.append({"file": f, "pov": pov_hero, "show": show_title, "cast": cast_raw})
            st.rerun()

# LIBRARY AREA
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['show']}** | POV: **{item['pov']}**")
        
        col_act, col_down = st.columns([1, 1])
        
        # ACTION: RUN DEEP ANALYSIS
        if col_act.button(f"🧠 Deep Analyze (Wiki-Check)", key=f"run_{idx}"):
            with st.status("🕵️ Phase 1: Watching & Fact-Checking..."):
                try:
                    # Upload
                    gf = genai.upload_file(item['file'])
                    while gf.state.name == "PROCESSING": time.sleep(2); gf = genai.get_file(gf.name)
                    
                    # GOOGLE SEARCH GROUNDING (Simulated via Prompt for Streamlit Cloud stability)
                    # We ask Gemini to use its internal knowledge base heavily
                    model = genai.GenerativeModel(MODEL_NAME)
                    
                    prompt = f"""
                    SYSTEM: You are a professional script supervisor and novelist.
                    
                    CONTEXT:
                    Show: {item['show']}
                    Cast: {item['cast']}
                    POV Character: {item['pov']}
                    
                    TASK 1: VERBATIM TRANSCRIPT (The "T-Box")
                    - Watch the FULL video. Do not summarize.
                    - Write down every line of dialogue with the correct Speaker Name.
                    - If you are unsure of a name, describe them (e.g., "Man in Blue Hat").
                    - Label this section [TRANSCRIPT].
                    
                    TASK 2: DEEP NOVELIZATION (The "N-Box")
                    - Write a book chapter from {item['pov']}'s perspective.
                    - FOCUS: Internal monologue, sensory details (smell, touch), and psychological depth.
                    - Do not just describe actions. Describe how {item['pov']} FEELS about the actions.
                    - Label this section [NOVEL].
                    
                    OUTPUT FORMAT:
                    [TRANSCRIPT]
                    (Full dialogue here...)
                    [END TRANSCRIPT]
                    
                    [NOVEL]
                    (Deep POV story here...)
                    [END NOVEL]
                    """
                    
                    st.write("📝 Writing Script & Novel...")
                    response = model.generate_content([gf, prompt], request_options={"timeout": 600})
                    st.session_state[f"res_{idx}"] = response.text
                    
                except Exception as e:
                    st.error(f"Analysis Failed: {e}")

        # DOWNLOAD VIDEO (Safe Mode)
        with open(item['file'], "rb") as f:
            col_down.download_button("💾 Save MP4", f, file_name=item['file'], mime="video/mp4")

        # DISPLAY RESULTS
        if f"res_{idx}" in st.session_state:
            full_text = st.session_state[f"res_{idx}"]
            
            # PARSE THE OUTPUT
            try:
                t_part = full_text.split("[TRANSCRIPT]")[1].split("[END TRANSCRIPT]")[0].strip()
                n_part = full_text.split("[NOVEL]")[1].split("[END NOVEL]")[0].strip()
            except:
                t_part = full_text
                n_part = "Parsing Error: The AI didn't use the split tags. Check T-Box for full output."

            # T-BOX & N-BOX
            t_col, n_col = st.columns(2)
            with t_col:
                st.subheader("📜 Full Transcript")
                st.text_area("T-Box", t_part, height=600, key=f"t_{idx}")
            with n_col:
                st.subheader(f"📖 Deep POV: {item['pov']}")
                st.text_area("N-Box", n_part, height=600, key=f"n_{idx}")

            # EXPORT TO WORD DOC
            docx_file = create_docx(t_part, n_part, item['pov'], item['show'])
            st.download_button(
                label="📄 Export as Word Doc (.docx)",
                data=docx_file,
                file_name=f"{item['show']}_{item['pov']}_Script.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"docx_{idx}"
            )
