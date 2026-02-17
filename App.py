import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIG ---
st.set_page_config(page_title="POV Director's Cut 2026", layout="wide")
MODEL_ID = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. WORD EXPORT ---
def create_docx(transcript, novel, pov, show):
    doc = Document()
    doc.add_heading(f"{show}: {pov} POV", 0)
    doc.add_heading('Transcript', level=1)
    doc.add_paragraph(transcript)
    doc.add_page_break()
    doc.add_heading('Deep POV Novel', level=1)
    doc.add_paragraph(novel)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("🎬 Studio Setup")
    show_name = st.text_input("Show:", "Wizards Beyond Waverly Place")
    cast_input = st.text_area("Cast:", "Roman: Wizard\nBillie: Lead\nGiada: Mom")
    cast_list = [c.split(":")[0].strip() for c in cast_input.split("\n") if ":" in c]
    pov_hero = st.selectbox("POV:", cast_list)
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

# --- 4. PRODUCTION ENGINE ---
st.title(f"🎬 {show_name} Production")
link = st.text_input("Video Link:")

if st.button("🚀 Record Episode") and link:
    fn = f"master_{datetime.now().strftime('%H%M%S')}.mp4"
    # Using H.264 for mobile stability
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, link]
    if c_file:
        with open("c.txt", "wb") as f: f.write(c_file.getbuffer())
        cmd.extend(["--cookies", "c.txt"])
    
    with st.status("🎬 Recording..."):
        subprocess.run(cmd)
    
    if os.path.exists(fn):
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 5. AI ANALYSIS ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['file']}** | **POV:** {item['pov']}")
        
        if st.button("✨ Deep Analysis (Fixed)", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is processing..."):
                try:
                    # ✅ FIXED LINE 75: Changed 'path=' to 'file='
                    file_upload = client.files.upload(file=item['file'])
                    
                    while file_upload.state == "PROCESSING":
                        time.sleep(3)
                        file_upload = client.files.get(name=file_upload.name)

                    # ✅ FIXED TOOL: Correct 2026 Search syntax
                    search_tool = types.Tool(google_search={})

                    prompt = f"""
                    1. Search Google for the official episode recap of '{item['show']}' to ensure name accuracy.
                    2. Watch the video. Write a FULL VERBATIM TRANSCRIPT. Do not skip lines. Identify: {item['cast']}.
                    3. Write a DEEP POV Novel chapter from {item['pov']}'s perspective.
                    Format as: [TRANSCRIPT] ... [END TRANSCRIPT] and [NOVEL] ... [END NOVEL]
                    """

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_upload, prompt],
                        config=types.GenerateContentConfig(tools=[search_tool])
                    )
                    st.session_state[f"res_{idx}"] = response.text
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 6. DISPLAY RESULTS ---
        if f"res_{idx}" in st.session_state:
            res = st.session_state[f"res_{idx}"]
            try:
                t = res.split("[TRANSCRIPT]")[1].split("[END TRANSCRIPT]")[0].strip()
                n = res.split("[NOVEL]")[1].split("[END NOVEL]")[0].strip()
            except:
                t, n = res, "Check transcript box for full output."

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📜 Transcript")
                st.text_area("T-Box", t, height=450, key=f"tbox_{idx}")
            with col2:
                st.subheader(f"📖 {item['pov']}'s Novel")
                st.text_area("N-Box", n, height=450, key=f"nbox_{idx}")
            
            st.download_button("📄 Download .docx", create_docx(t, n, item['pov'], item['show']), file_name=f"{item['pov']}_Script.docx")
