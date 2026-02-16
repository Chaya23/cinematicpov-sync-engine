import streamlit as st
import google.generativeai as genai
import time
import subprocess
from docx import Document
from io import BytesIO

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence for outputs
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# 2. SEPARATE EXPORT ENGINE
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def download_video_url(url, cookies=None):
    out = "downloaded_vid.mp4"
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", out, url]
    if cookies:
        cmd.extend(["--cookies", cookies])
    subprocess.run(cmd, check=True)
    return out

# 3. SIDEBAR: THE CAST BIBLE
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area("Update Cast Roles:", 
        "Giada: Mother (Mortal)\nJustin: Father (Wizard)\nRoman: Protagonist (Son)\nTheresa: Grandmother\nBillie: Protagonist (Sister)")
    pov_choice = st.selectbox("Novel Narrator:", ["Roman Russo", "Billie", "Justin"])
    st.divider()
    cookie_file = st.file_uploader("Optional: Upload cookies.txt", type=["txt"])

# 4. TABBED INTERFACE (Mobile Friendly)
tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Recording"])

# --- TAB 1: LOCAL FILE ---
with tab1:
    st.subheader("Upload Episode File")
    file_vid = st.file_uploader("Choose MP4/MOV", type=["mp4", "mov"], key="file_up")

# --- TAB 2: URL SYNC ---
with tab2:
    st.subheader("Sync via Link")
    url_link = st.text_input("Paste YouTube or Disney+ URL:")
    st.caption("Note: Use the sidebar to upload cookies if this is a paid subscription link.")

# --- TAB 3: LIVE RECORDING ---
with tab3:
    st.subheader("Author's Live Notes")
    live_audio = st.audio_input("Record plot ideas or live reactions:")
    live_text = st.text_area("Live Commentary / Plot Tweaks:")

# 5. THE PRODUCTION BUTTON
if st.button("🚀 START PRODUCTION (All Tabs)", use_container_width=True):
    with st.status("🎬 Gemini 2.5 Flash is analyzing...") as status:
        try:
            # Determine Source
            source_path = ""
            if file_vid:
                source_path = "input_vid.mp4"
                with open(source_path, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                c_path = "temp_cookies.txt" if cookie_file else None
                if cookie_file:
                    with open(c_path, "wb") as f: f.write(cookie_file.getbuffer())
                source_path = download_video_url(url_link, c_path)
            
            if not source_path:
                st.error("Please provide a video source (Upload or URL)!")
            else:
                # Upload to AI
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                genai_file = genai.upload_file(path=source_path)
                while genai_file.state.name == "PROCESSING":
                    time.sleep(5)
                    genai_file = genai.get_file(genai_file.name)

                # Prompt construction including Live Notes
                full_prompt = f"""
                Cast List: {cast_info}
                Live Author Notes: {live_text}
                
                1. Provide a FULL VERBATIM TRANSCRIPT.
                ---SPLIT---
                2. Write a 2500-word novel chapter from {pov_choice}'s POV.
                """
                
                response = model.generate_content([genai_file, full_prompt])
                
                if "---SPLIT---" in response.text:
                    parts = response.text.split("---SPLIT---")
                    st.session_state.transcript = parts[0]
                    st.session_state.chapter = parts[1]
                
                status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Error: {e}")

# 6. THE DOWNLOAD HUB (Separate Word Docs)
if st.session_state.transcript:
    st.divider()
    st.subheader("📥 Export Production Files")
    c1, c2 = st.columns(2)
    
    with c1:
        st.download_button(
            label="💾 Download Full Transcript (.docx)",
            data=create_docx("Verbatim Transcript", st.session_state.transcript),
            file_name="Episode_Transcript.docx",
            use_container_width=True
        )
    
    with c2:
        st.download_button(
            label="💾 Download Roman's Novel (.docx)",
            data=create_docx(f"{pov_choice} POV Novel", st.session_state.chapter),
            file_name="Novel_Chapter.docx",
            use_container_width=True
        )
