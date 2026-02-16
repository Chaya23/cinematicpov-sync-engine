import streamlit as st
import google.generativeai as genai
import subprocess
import time
import os
from docx import Document
from io import BytesIO

# 1. SETUP
st.set_page_config(page_title="Wizards Fanfic Master Studio", layout="wide")
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# 2. THE DOCUMENT & DOWNLOAD ENGINE
def create_docx(title, text):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def download_video(url, cookie_file=None):
    out = "episode_full.mp4"
    # Basic command for yt-dlp
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", out, url]
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    subprocess.run(cmd, check=True)
    return out

# 3. SIDEBAR: CUSTOM FANFIC & POV EDIT
with st.sidebar:
    st.header("🎭 Fanfic Editor")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Justin", "Billie", "Alex"])
    genre = st.selectbox("Style:", ["General Fiction", "Angst", "Action", "Comedy"])
    
    st.divider()
    st.header("🔑 Login Access")
    cookie_txt = st.file_uploader("Upload cookies.txt for Disney+/YT", type=["txt"])
    st.info("Use a browser extension to export Netscape format cookies.")

# 4. LIVE RECORDING & URL INPUT
st.title("🧙‍♂️ Roman's Redemption: Ultimate Studio")
url_input = st.text_input("Paste Video URL (YouTube/Disney+):", placeholder="https://...")
up_file = st.file_uploader("OR Upload Video Manually", type=["mp4", "mov"])

with st.expander("🎙️ Live Plot Recording"):
    audio_note = st.audio_input("Record your thoughts for the AI to include:")
    custom_hooks = st.text_area("Specific Scene Requests:", "Make Roman realize his worth without the magic shirt.")

# 5. PRODUCTION
if st.button("🔥 Generate Full Production"):
    try:
        with st.status("🚀 Processing Full 23-Minute Episode...") as status:
            # Step A: Get the File
            if up_file:
                video_path = "manual_upload.mp4"
                with open(video_path, "wb") as f: f.write(up_file.getbuffer())
            else:
                c_path = "cookies.txt" if cookie_txt else None
                if cookie_txt:
                    with open(c_path, "wb") as f: f.write(cookie_txt.getbuffer())
                video_path = download_video(url_input, c_path)

            # Step B: AI Upload
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            vid_file = genai.upload_file(path=video_path)
            while vid_file.state.name == "PROCESSING":
                time.sleep(8)
                vid_file = genai.get_file(vid_file.name)

            # Step C: The Mega Prompt
            prompt = f"""
            Identify all characters. 
            TASK 1: FULL TRANSCRIPT. Transcribe all 23 minutes. Labeled [Time] Name: Dialogue.
            TASK 2: NOVEL CHAPTER. Write a deep-POV chapter for {pov_choice} in {genre} style.
            Include Roman's internal thoughts and interactions. Use these notes: {custom_hooks}
            """
            
            response = model.generate_content([vid_file, prompt])
            
            # Logic to split transcript and chapter
            if "TASK 2" in response.text:
                parts = response.text.split("TASK 2")
                st.session_state.transcript = parts[0]
                st.session_state.chapter = parts[1]
            else:
                st.session_state.chapter = response.text
            
            status.update(label="✅ Masterpiece Ready!", state="complete")
    except Exception as e:
        st.error(f"Error: {e}")

# 6. DOWNLOADS
if st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 Complete Transcript")
        st.download_button("📥 Download .docx", create_docx("Full Transcript", st.session_state.transcript), "transcript.docx")
        st.text_area("View", st.session_state.transcript, height=300)
    with col2:
        st.subheader(f"📖 {pov_choice}'s Chapter")
        st.download_button("📥 Download .docx", create_docx(f"{pov_choice} Story", st.session_state.chapter), "chapter.docx")
        st.text_area("View", st.session_state.chapter, height=300)
