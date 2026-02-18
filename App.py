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

# --- 1. SETUP ---
st.set_page_config(page_title="POV Studio 2026", layout="wide", page_icon="🎬")
MODEL_ID = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

# Initialize Client
api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. DOCX EXPORT ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. SIDEBAR: SMART CAST & POV ---
with st.sidebar:
    st.header("🎬 Studio Setup")
    show_name = st.text_input("Show Title:", "Wizards Beyond Waverly Place")
    
    # EDITABLE CAST LIST
    cast_input = st.text_area(
        "Edit Cast List (Name: Role):", 
        "Roman: Wizard Son\nBillie: Lead\nGiada: Mom\nJustin: Dad",
        height=150
    )
    
    # DYNAMIC POV SELECTOR
    # This regex finds names before the colon to update the dropdown instantly
    names = [n.strip() for n in re.findall(r'^([^:]+):', cast_input, flags=re.MULTILINE)]
    if not names: names = ["Default"]
    
    pov_hero = st.selectbox("Select Narrator POV:", options=names)
    
    st.divider()
    st.info("🦊 Best with Firefox cookies for Disney+")
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

# --- 4. PRODUCTION INPUTS ---
st.title(f"🎬 {show_name} Production Studio")

tab1, tab2 = st.tabs(["🔗 Record from URL", "📂 Upload Local Video"])

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
    local_file = st.file_uploader("Select video file:", type=["mp4", "mkv", "mov"])
    if st.button("⬆️ Process Upload") and local_file:
        fn = f"local_{local_file.name}"
        with open(fn, "wb") as f:
            f.write(local_file.getbuffer())
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 5. STREAMING PRODUCTION ENGINE (65K TOKENS) ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **Source:** {item['file']} | **POV Target:** {item['pov']}")
        
        if st.button("✨ Run High-Accuracy Production", key=f"ai_{idx}"):
            res_area = st.empty() # Placeholder for streaming text
            full_text = ""
            
            with st.status("🧠 Gemini 3 Pro is processing..."):
                try:
                    # Upload
                    file_up = client.files.upload(file=item['file'])
                    while file_up.state == "PROCESSING":
                        time.sleep(3)
                        file_up = client.files.get(name=file_up.name)

                    # Config with 65k output limit and Search Tool
                    config = types.GenerateContentConfig(
                        max_output_tokens=65000,
                        temperature=0.7,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )

                    prompt = f"""
                    1. Research '{item['show']}' and character list: {item['cast']} via Google Search.
                    2. Watch the video.
                    3. TASK 1: FULL VERBATIM TRANSCRIPT. Word-for-word. Identify: {item['cast']}.
                    4. TASK 2: DEEP POV NOVEL. Write a long chapter from {item['pov']}'s POV.
                    
                    Use these markers exactly:
                    [TRANSCRIPT]
                    [END_TRANSCRIPT]
                    [NOVEL]
                    [END_NOVEL]
                    """

                    # STREAMING to avoid the 400 'Length too long' error
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_up, prompt],
                        config=config,
                        stream=True
                    )
                    
                    for chunk in response:
                        full_text += chunk.text
                        res_area.write(f"✍️ Streaming Output: {len(full_text.split())} words generated...")

                    st.session_state[f"res_{idx}"] = full_text
                    st.success("✅ Content Generated!")
                    st.rerun()

                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 6. DISPLAY & DOWNLOAD ---
        if f"res_{idx}" in st.session_state:
            raw = st.session_state[f"res_{idx}"]
            try:
                t = raw.split("[TRANSCRIPT]")[1].split("[END_TRANSCRIPT]")[0].strip()
                n = raw.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
            except:
                t, n = raw, "Check Transcript box for full raw data."

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📜 Verbatim Transcript")
                st.text_area("T-Box", t, height=500, key=f"t_{idx}")
                st.download_button("📥 Save Transcript", create_docx(t, "Transcript"), file_name=f"Transcript_{idx}.docx")
            
            with c2:
                st.subheader(f"📖 {item['pov']}'s POV Novel")
                st.text_area("N-Box", n, height=500, key=f"n_{idx}")
                st.download_button("📥 Save Novel", create_docx(n, f"{item['pov']} POV"), file_name=f"Novel_{item['pov']}.docx")
