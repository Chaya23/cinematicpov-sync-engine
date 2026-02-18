import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. SETUP ---
st.set_page_config(page_title="POV Cinema DVR 2026", layout="wide")
MODEL_ID = "gemini-3-pro-preview" # The 2026 Flagship

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. WORD DOC UTILITY ---
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. SIDEBAR: CHARACTER & POV ---
with st.sidebar:
    st.header("🎭 Show Production")
    show_name = st.text_input("Show Title:", "Wizards Beyond Waverly Place")
    
    # MASTER CHARACTER LIST
    cast_raw = st.text_area(
        "Character List (Name: Role):", 
        "Roman: Wizard Son\nBillie: Lead Apprentice\nGiada: Mom\nJustin: Dad/Teacher\nMilo: Younger Brother"
    )
    
    # DYNAMIC DROPDOWN: Pulls names from the text area above
    names = [line.split(":")[0].strip() for line in cast_raw.split("\n") if ":" in line]
    if not names: names = ["Select a character..."]
    
    pov_hero = st.selectbox("Narrator POV:", names)
    
    st.divider()
    c_file = st.file_uploader("🍪 Upload cookies.txt", type="txt")

# --- 4. DVR ENGINE ---
st.title(f"🎬 {show_name} Studio")
link = st.text_input("Paste Link:")

if st.button("🚀 Record & Analyze") and link:
    fn = f"master_{datetime.now().strftime('%H%M%S')}.mp4"
    # Forced H.264 for mobile playback
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, link]
    if c_file:
        with open("c.txt", "wb") as f: f.write(c_file.getbuffer())
        cmd.extend(["--cookies", "c.txt"])
    
    with st.status("🎬 Recording 24-minute episode..."):
        subprocess.run(cmd)
    
    if os.path.exists(fn):
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_raw, "pov": pov_hero})
        st.rerun()

# --- 5. AI PRODUCTION ENGINE ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **File:** {item['file']} | **POV:** {item['pov']}")
        
        if st.button("✨ Run AI (Wiki-Check + Full Transcript)", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is Grounding & Transcribing..."):
                try:
                    # Upload video to Google Cloud
                    file_up = client.files.upload(file=item['file'])
                    while file_up.state == "PROCESSING":
                        time.sleep(3)
                        file_up = client.files.get(name=file_up.name)

                    # 2026 SEARCH TOOL (Wiki Grounding)
                    search_tool = types.Tool(google_search={})

                    # CONFIG: 65k Output tokens (Infinite Script)
                    config = types.GenerateContentConfig(
                        max_output_tokens=65000,
                        temperature=0.7,
                        tools=[search_tool]
                    )

                    prompt = f"""
                    1. SEARCH GOOGLE: Look up the official episode recap for '{item['show']}' and character names: {item['cast']}.
                    2. VIDEO ANALYSIS: Watch the full video.
                    3. TRANSCRIPT: Provide a VERBATIM, word-for-word transcript. Identify speakers correctly.
                    4. NOVEL: Write a deep, sensory-heavy 1st person chapter from {item['pov']}'s POV. 
                       Include internal monologue and psychological depth.
                    
                    Format your response with these exact tags:
                    [TRANSCRIPT]
                    (Text here)
                    [END_TRANSCRIPT]
                    [NOVEL]
                    (Text here)
                    [END_NOVEL]
                    """

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_up, prompt],
                        config=config
                    )
                    st.session_state[f"res_{idx}"] = response.text
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 6. DISPLAY & SEPARATE EXPORTS ---
        if f"res_{idx}" in st.session_state:
            raw = st.session_state[f"res_{idx}"]
            try:
                t_part = raw.split("[TRANSCRIPT]")[1].split("[END_TRANSCRIPT]")[0].strip()
                n_part = raw.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
            except:
                t_part, n_part = raw, "Split failed. Check full text."

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📜 Verbatim Transcript")
                st.text_area("T-Box", t_part, height=450, key=f"t_{idx}")
                # SEPARATE DOWNLOAD 1
                st.download_button(
                    "📥 Download Transcript (.docx)", 
                    create_docx(t_part, "Full Transcript"), 
                    file_name="Transcript.docx"
                )
            
            with col2:
                st.subheader(f"📖 {item['pov']}'s Novel")
                st.text_area("N-Box", n_part, height=450, key=f"n_{idx}")
                # SEPARATE DOWNLOAD 2
                st.download_button(
                    "📥 Download Novel (.docx)", 
                    create_docx(n_part, f"Novel: {item['pov']} POV"), 
                    file_name=f"Novel_{item['pov']}.docx"
                )
