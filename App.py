import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIG & CLIENT ---
st.set_page_config(page_title="POV Director's Cut 2026", layout="wide")

# Using the Feb 2026 flagship model
MODEL_ID = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

# Initialize the new 2026 Client
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

# --- 3. DVR DOWNLOADER ---
def dvr_download(url, cookies=None):
    fn = f"master_{datetime.now().strftime('%H%M%S')}.mp4"
    cmd = ["yt-dlp", "-f", "mp4", "-o", fn, url]
    if cookies:
        with open("c.txt", "wb") as f: f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "c.txt"])
    with st.status("🎬 Recording..."):
        subprocess.run(cmd)
    return fn if os.path.exists(fn) else None

# --- 4. UI ---
with st.sidebar:
    st.header("🎬 Studio Setup")
    show_name = st.text_input("Show:", "Wizards Beyond Waverly Place")
    cast_input = st.text_area("Cast (Name: Role):", "Roman: Wizard\nBillie: Lead\nGiada: Mom")
    cast_list = [c.split(":")[0].strip() for c in cast_input.split("\n") if ":" in c]
    pov_hero = st.selectbox("POV:", cast_list)
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

st.title(f"🎬 {show_name} Production")
link = st.text_input("Video Link:")

if st.button("🚀 Record Episode") and link:
    video_file = dvr_download(link, c_file)
    if video_file:
        st.session_state.library.append({"file": video_file, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 5. PRODUCTION ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['file']}** | **POV:** {item['pov']}")
        
        if st.button("✨ Deep Analysis (With Wiki-Search)", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is processing..."):
                # Upload to GenAI File API
                file_upload = client.files.upload(path=item['file'])
                while file_upload.state == "PROCESSING":
                    time.sleep(2)
                    file_upload = client.files.get(name=file_upload.name)

                # The 2026 Google Search Tool Configuration
                search_tool = types.Tool(google_search=types.GoogleSearch())

                prompt = f"""
                1. Search Google for the official episode recap of '{item['show']}' to ensure name accuracy.
                2. Watch the video. Write a FULL VERBATIM TRANSCRIPT. Do not skip lines.
                3. Write a DEEP POV Novel chapter from {item['pov']}'s perspective (emotions, senses, thoughts).
                Format as: [TRANSCRIPT] ... [END TRANSCRIPT] and [NOVEL] ... [END NOVEL]
                """

                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=[file_upload, prompt],
                    config=types.GenerateContentConfig(tools=[search_tool])
                )
                st.session_state[f"res_{idx}"] = response.text

        if f"res_{idx}" in st.session_state:
            res = st.session_state[f"res_{idx}"]
            try:
                t = res.split("[TRANSCRIPT]")[1].split("[END TRANSCRIPT]")[0].strip()
                n = res.split("[NOVEL]")[1].split("[END NOVEL]")[0].strip()
            except:
                t, n = res, "Formatting error. Check transcript box."

            c1, c2 = st.columns(2)
            c1.text_area("T-Box", t, height=400)
            c2.text_area("N-Box", n, height=400)
            
            st.download_button("📄 Download .docx", create_docx(t, n, item['pov'], item['show']), file_name="Script.docx")
