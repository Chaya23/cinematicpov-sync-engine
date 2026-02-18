import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
import re
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Cinematic POV Sync v2026", layout="wide")
MODEL_ID = "gemini-3-pro-preview"

# Initialize Session State
if "library" not in st.session_state:
    st.session_state.library = []

# API Client
api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. WORD EXPORT UTILITY ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. SIDEBAR: THE AUTOMATIC POV SYNC ---
with st.sidebar:
    st.header("🎬 Studio Setup")
    show_name = st.text_input("Show Title:", "Wizards Beyond Waverly Place")
    
    # CAST LIST: The Master Source
    cast_input = st.text_area(
        "Edit Cast (Name: Role):", 
        "Roman: Wizard\nBillie: Lead\nGiada: Mom\nJustin: Dad",
        height=150
    )
    
    # ⚡ SMART POV SELECTOR: 
    # This automatically scans your Cast List for names every time you type.
    found_names = [n.strip() for n in re.findall(r'^([^:]+):', cast_input, flags=re.MULTILINE)]
    if not found_names: found_names = ["Unknown"]
    
    pov_hero = st.selectbox("Narrator POV:", found_names)
    
    st.divider()
    st.info("🦊 Tip: Export your Disney+ cookies from Firefox for the best DVR results.")
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

# --- 4. VIDEO INPUTS: URL OR UPLOAD ---
st.title(f"🎬 {show_name} Production")

# Create two tabs: one for live recording, one for pre-recorded files
tab1, tab2 = st.tabs(["🚀 Record Disney+ Link", "📂 Upload Recorded Video"])

with tab1:
    link = st.text_input("Video URL:")
    if st.button("🔴 Start DVR") and link:
        fn = f"dvr_{datetime.now().strftime('%H%M%S')}.mp4"
        cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, link]
        if c_file:
            with open("c.txt", "wb") as f: f.write(c_file.getbuffer())
            cmd.extend(["--cookies", "c.txt"])
        with st.status("🎬 Recording..."):
            subprocess.run(cmd)
        if os.path.exists(fn):
            st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
            st.rerun()

with tab2:
    uploaded_file = st.file_uploader("Select a video from your device:", type=["mp4", "mkv", "mov"])
    if st.button("⬆️ Process Uploaded Video") and uploaded_file:
        fn = f"local_{uploaded_file.name}"
        with open(fn, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 5. THE AI PRODUCTION ENGINE ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['file']}** | **POV:** {item['pov']}")
        
        if st.button("✨ Start High-Accuracy Production", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is processing with expanded tokens..."):
                try:
                    # ✅ FIXED: SDK 2026 file upload parameter 'file='
                    file_upload = client.files.upload(file=item['file'])
                    while file_upload.state == "PROCESSING":
                        time.sleep(3)
                        file_upload = client.files.get(name=file_upload.name)

                    # ✅ FIXED: 2026 Search Tool Syntax
                    search_tool = types.Tool(google_search=types.GoogleSearch())

                    # ✅ EXPANDED TOKENS (65.5k for the 24-minute verbatim script)
                    config = types.GenerateContentConfig(
                        max_output_tokens=65000,
                        temperature=0.8,
                        tools=[search_tool]
                    )

                    prompt = f"""
                    1. SEARCH GOOGLE: Research 'Wizards Beyond Waverly Place' episode recaps and the official Wiki. 
                    Ensure names like Roman, Billie, and Giada are accurately identified.
                    2. VIDEO ANALYSIS: Watch the video. 
                    3. TASK A: FULL VERBATIM TRANSCRIPT. Identify characters from list: {item['cast']}.
                    4. TASK B: DEEP POV NOVEL. Write a long, immersive 1st-person chapter from {item['pov']}'s POV.
                    
                    Format your response with these tags:
                    [TRANSCRIPT] ... [END_TRANSCRIPT]
                    [NOVEL] ... [END_NOVEL]
                    """

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_upload, prompt],
                        config=config
                    )
                    st.session_state[f"res_{idx}"] = response.text
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 6. SEPARATE BOXES & DOWNLOADS ---
        if f"res_{idx}" in st.session_state:
            res = st.session_state[f"res_{idx}"]
            try:
                t = res.split("[TRANSCRIPT]")[1].split("[END_TRANSCRIPT]")[0].strip()
                n = res.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
            except:
                t, n = res, "Check transcript box for full raw output."

            col_t, col_n = st.columns(2)
            with col_t:
                st.subheader("📜 Verbatim Transcript")
                st.text_area("T-Box", t, height=450, key=f"tbox_{idx}")
                # SEPARATE DOWNLOAD 1
                st.download_button("📥 Download Transcript (.docx)", 
                                   create_docx(t, "Full Transcript"), 
                                   file_name=f"Transcript_{idx}.docx")
            
            with col_n:
                st.subheader(f"📖 {item['pov']}'s Novel")
                st.text_area("N-Box", n, height=450, key=f"nbox_{idx}")
                # SEPARATE DOWNLOAD 2
                st.download_button("📥 Download Novel (.docx)", 
                                   create_docx(n, f"Novel Chapter: {item['pov']} POV"), 
                                   file_name=f"Novel_{item['pov']}.docx")
