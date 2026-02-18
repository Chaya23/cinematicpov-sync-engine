import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
st.set_page_config(page_title="POV Cinema DVR 2026", layout="wide", page_icon="🎬")

# The 2026 Flagship Model (Expanded Tokens & Long Context)
MODEL_ID = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

# Initialize 2026 SDK Client
api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. DOCX EXPORT UTILITY ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. SIDEBAR: THE EDITABLE CAST & POV ---
with st.sidebar:
    st.header("🎭 Show Production")
    show_name = st.text_input("Show Title:", "Wizards Beyond Waverly Place")
    
    # MASTER CAST LIST (Editable)
    cast_raw = st.text_area(
        "Edit Cast List (Name: Role):", 
        "Roman: Wizard Son\nBillie: Apprentice\nGiada: Mom\nJustin: Dad\nMilo: Brother",
        height=150
    )
    
    # DYNAMIC POV SYNC: Automatically extracts names for the dropdown
    # If you add 'Winter' to the text area, she appears here immediately.
    available_names = [line.split(":")[0].strip() for line in cast_raw.split("\n") if ":" in line]
    if not available_names: 
        available_names = ["Select Character"]
        
    pov_hero = st.selectbox("Narrator POV:", options=available_names)
    
    st.divider()
    st.subheader("🍪 Connection")
    c_file = st.file_uploader("Upload Firefox cookies.txt", type="txt")

# --- 4. THE MULTI-INPUT STUDIO (URL or UPLOAD) ---
st.title(f"🎬 {show_name} Studio")

tab_url, tab_upload = st.tabs(["🔗 Record from URL", "📂 Upload Recorded Video"])

with tab_url:
    link = st.text_input("Paste Disney+ / Netflix Link:")
    record_btn = st.button("🔴 Start DVR Recording")

with tab_upload:
    uploaded_video = st.file_uploader("Upload an MP4 already on your device:", type=["mp4", "mkv", "mov"])
    upload_btn = st.button("⬆️ Process Uploaded File")

# Handle DVR Input
if record_btn and link:
    fn = f"dvr_{datetime.now().strftime('%H%M%S')}.mp4"
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, link]
    if c_file:
        with open("c.txt", "wb") as f: f.write(c_file.getbuffer())
        cmd.extend(["--cookies", "c.txt"])
    
    with st.status("🎬 DVR in progress (Firefox Sync)..."):
        subprocess.run(cmd)
    
    if os.path.exists(fn):
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_raw, "pov": pov_hero})
        st.rerun()

# Handle Manual Upload Input
if upload_btn and uploaded_video:
    fn = f"upload_{uploaded_video.name}"
    with open(fn, "wb") as f:
        f.write(uploaded_video.getbuffer())
    st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_raw, "pov": pov_hero})
    st.rerun()

# --- 5. AI PRODUCTION ENGINE (GEMINI 3 PRO) ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **Ready:** {item['file']} | **POV:** {item['pov']}")
        
        if st.button("✨ Run High-Accuracy Production", key=f"ai_{idx}"):
            with st.status("🧠 AI is watching & checking Wiki recaps..."):
                try:
                    # 1. Upload Video to AI Cloud
                    file_up = client.files.upload(file=item['file'])
                    while file_up.state == "PROCESSING":
                        time.sleep(3)
                        file_up = client.files.get(name=file_up.name)

                    # 2. Configure 2026 Google Search & Tokens
                    search_tool = types.Tool(google_search={})
                    config = types.GenerateContentConfig(
                        max_output_tokens=65000, # Expanded tokens for full 24m transcript
                        temperature=0.7,
                        tools=[search_tool]
                    )

                    # 3. The Instruction
                    prompt = f"""
                    WATCH: The full video provided.
                    SEARCH: Look up the official episode recap for '{item['show']}' and character list: {item['cast']}.
                    
                    TASK 1: FULL VERBATIM TRANSCRIPT
                    - Transcribe every word. No summaries. 
                    - Use character names correctly. Identify: {item['cast']}.
                    - Format: [TRANSCRIPT] ... [END_TRANSCRIPT]
                    
                    TASK 2: DEEP POV NOVEL
                    - Write a full literary chapter from {item['pov']}'s perspective.
                    - Use 1st person. Include sensory details and internal thoughts.
                    - Format: [NOVEL] ... [END_NOVEL]
                    """

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_up, prompt],
                        config=config
                    )
                    st.session_state[f"res_{idx}"] = response.text
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 6. DUAL-BOX DISPLAY & DOWNLOADS ---
        if f"res_{idx}" in st.session_state:
            raw = st.session_state[f"res_{idx}"]
            try:
                t_part = raw.split("[TRANSCRIPT]")[1].split("[END_TRANSCRIPT]")[0].strip()
                n_part = raw.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
            except:
                t_part, n_part = raw, "Parsing error. Check Full Output."

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📜 Verbatim Transcript")
                st.text_area("T-Box", t_part, height=500, key=f"t_{idx}")
                st.download_button("📥 Download Transcript (.docx)", 
                                   create_docx(t_part, "Transcript"), 
                                   file_name=f"Transcript_{idx}.docx")
            
            with col2:
                st.subheader(f"📖 {item['pov']}'s Novel")
                st.text_area("N-Box", n_part, height=500, key=f"n_{idx}")
                st.download_button("📥 Download Novel (.docx)", 
                                   create_docx(n_part, f"Novel - {item['pov']} POV"), 
                                   file_name=f"Novel_{item['pov']}.docx")
