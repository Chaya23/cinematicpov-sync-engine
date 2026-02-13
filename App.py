import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import yt_dlp

# --- 1. CORE CONFIG ---
st.set_page_config(page_title="CinematicPOV Fusion v17.5", layout="wide", page_icon="🕵️")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Add them to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. THE STEALTH ENGINE (Private Browsing Spoofing) ---
def download_video_stealth(url, tmp_dir):
    """Uses deep spoofing to bypass Disney/Solar 'Access Denied' blocks."""
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'quiet': True,
        'nocheckcertificate': True,
        # This mimics a private Chrome session on Windows
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
        },
        'cookiesfrombrowser': ('chrome',), # Attempts to use your local Chrome cookies if available
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            st.error(f"Host Blocked Access: {e}")
            return None
            
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"): return os.path.join(tmp_dir, f)
    return None

# --- 3. DOCUMENT ARCHIVE ENGINE ---
def create_archive_docx(transcript, chapter, pov_name):
    doc = Document()
    doc.add_heading(f'ARCHIVE: JUSTICE FOR {pov_name.upper()}', 0)
    
    doc.add_heading('Official Line-by-Line Speaker Transcript', level=1)
    doc.add_paragraph(transcript)
    
    doc.add_page_break()
    
    doc.add_heading(f'Novelization: {pov_name}\'s True Point of View', level=1)
    doc.add_paragraph(chapter)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 4. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Fusion v17.5")
st.markdown("### *Bypassing the 'Alex Bias' for Roman's Story*")

url_input = st.text_input("Paste Disney/Solar/YouTube URL:")
uploaded_video = st.file_uploader("OR Upload File (Safest Bypass):", type=['mp4', 'webm', 'mkv'])

with st.sidebar:
    st.header("🎭 Character Sync")
    cast = st.text_area("Cast Names:", "Roman, Billie, Justin, Winter, Milo, Giada")
    pov_char = st.selectbox("Focus Character (Novel POV):", [c.strip() for c in cast.split(",")])
    st.divider()
    st.warning("Note: Private Spoofing is active. If URLs still fail, use the 'Upload' button.")

if st.button("🚀 EXECUTE STEALTH FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # STEP 1: VIDEO ACQUISITION
        video_path = ""
        if uploaded_video:
            video_path = os.path.join(tmp_dir, uploaded_video.name)
            with open(video_path, "wb") as f: f.write(uploaded_video.getbuffer())
        else:
            st.info("🕵️ Initiating Stealth Bypass...")
            video_path = download_video_stealth(url_input, tmp_dir)

        if not video_path:
            st.error("Access Denied. The host blocked the AI. Please download the video to your phone/PC and upload it here.")
            st.stop()

        # STEP 2: WHISPER DIALOGUE
        st.info("👂 Extracting Verbatim Dialogue...")
        audio_path = os.path.join(tmp_dir, "audio.mp3")
        subprocess.run(f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y", shell=True, capture_output=True)
        with open(audio_path, "rb") as f_a:
            raw_transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=f_a, response_format="text")

        # STEP 3: GEMINI VISION SYNC
        st.info("☁️ Gemini: Matching Speaker Names to Transcript...")
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        # STEP 4: THE FUSION (No-Safety-Block Edition)
        safety = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        prompt = f"""
        WHISPER SCRIPT: {raw_transcript}
        CAST: {cast}
        
        TASK:
        1. SCRIPT: Use the video to identify which character said each line. 
           Format: [NAME]: [Dialogue]. Focus on accuracy.
        2. NOVEL: Write a YA chapter from {pov_char}'s POV. 
           Highlight his internal feelings of being ignored, undercut, or his frustration with the 'Alex-style' chaos.
           Focus on the bias shown by Justin and Giada toward Billie.
        
        FORMAT:
        ---SCRIPT---
        [Transcript]
        ---NOVEL---
        [Chapter]
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content([video_file, prompt], safety_settings=safety)
        genai.delete_file(video_file.name)

        if "---NOVEL---" in res.text:
            parts = res.text.split("---NOVEL---")
            st.session_state.final_script = parts[0].replace("---SCRIPT---", "").strip()
            st.session_state.final_novel = parts[1].strip()
            st.success("✅ Fusion Successful!")

# --- 5. RESULTS & DOWNLOAD ---
if "final_novel" in st.session_state:
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Official Transcript")
        st.text_area("Sync Data", st.session_state.final_script, height=400)
    with r:
        st.subheader(f"📖 {pov_char}'s Novel")
        st.text_area("Manuscript", st.session_state.final_novel, height=400)

    # Word Doc Download
    doc_bytes = create_archive_docx(st.session_state.final_script, st.session_state.final_novel, pov_char)
    st.download_button(
        label="📥 Download Archive (Transcript + Novel).docx",
        data=doc_bytes,
        file_name=f"Roman_Russo_Justice_{pov_char}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
