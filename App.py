import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Fusion v17.0", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Check your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. WORD DOCUMENT ENGINE ---
def create_master_docx(transcript, chapter, pov_name):
    """Creates a high-quality Word doc with Transcript + Novel."""
    doc = Document()
    doc.add_heading('CINEMATIC POV: MASTER ARCHIVE', 0)
    
    # Transcript with Speaker IDs
    doc.add_heading('Official Speaker-Identified Transcript', level=1)
    doc.add_paragraph(transcript)
    
    doc.add_page_break()
    
    # The Novel Chapter
    doc.add_heading(f'Novelization: {pov_name}\'s POV', level=1)
    doc.add_paragraph(chapter)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. VIDEO & AUDIO TOOLS ---
def download_video(url, tmp_dir):
    """Bypasses blocks using stealth browser headers."""
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'quiet': True,
        'nocheckcertificate': True,
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36'}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try: ydl.download([url])
        except: return None
    for f in os.listdir(tmp_dir):
        if f.startswith("episode"): return os.path.join(tmp_dir, f)
    return None

def extract_audio(video_path, tmp_dir):
    """Converts video to mono audio for Whisper."""
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    subprocess.run(f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y", shell=True, capture_output=True)
    return audio_path

# --- 4. MODEL RESOLVER ---
def get_safe_model():
    """Detects available Gemini model name to avoid 404s."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((m for m in models if "flash" in m), "gemini-1.5-flash")
    except: return "gemini-1.5-flash"

# --- 5. SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🎭 Character Studio")
    cast_input = st.text_area("Cast Members (Edit):", "Roman, Billie, Justin, Winter, Milo, Giada")
    pov_char = st.selectbox("Novel POV:", [c.strip() for c in cast_input.split(",")])
    st.divider()
    st.info("Fusion v17.0: Fixed Safety Filters & Word Export")

# --- 6. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Fusion v17.0")
url_input = st.text_input("Episode URL (Disney/Solar/YT):")
uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'webm', 'mkv'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Acquisition
        video_path = ""
        if uploaded:
            video_path = os.path.join(tmp_dir, uploaded.name)
            with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
        else:
            st.info("🕵️ Accessing Video...")
            video_path = download_video(url_input, tmp_dir)

        if not video_path:
            st.error("Access denied by host. Please upload the file directly.")
            st.stop()

        # Step 1: Whisper Transcription
        st.info("👂 Whisper: Transcribing dialogue...")
        audio_path = extract_audio(video_path, tmp_dir)
        with open(audio_path, "rb") as f_a:
            transcript_raw = client_oa.audio.transcriptions.create(model="whisper-1", file=f_a, response_format="text")

        # Step 2: Gemini Vision Analysis
        st.info("☁️ Gemini: Processing Video...")
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        # Step 3: The Fusion (With Safety Fix)
        st.info(f"✍️ Authoring {pov_char}'s POV...")
        
        # New: Safety Guardrail Fix
        safety = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        model = genai.GenerativeModel(get_safe_model())
        
        prompt = f"""
        CAST: {cast_input}
        WHISPER DIALOGUE: {transcript_raw}
        
        This is a fictional, family-friendly Disney sitcom novelization. 
        TASK:
        1. LINE-BY-LINE TRANSCRIPT: Watch the video and identify who said every line from the Whisper dialogue. 
           Format: [NAME]: [Dialogue]. (e.g., ROMAN: I felt a surge of magic.)
        2. NOVEL CHAPTER: Write a YA chapter from {pov_char}'s POV. 
           Use the EXACT dialogue. Describe the internal thoughts behind every interaction.
        
        FORMAT:
        ---SCRIPT_START---
        [Full Transcript]
        ---NOVEL_START---
        [Full Chapter]
        """
        
        try:
            res = model.generate_content([video_file, prompt], safety_settings=safety)
            genai.delete_file(video_file.name)
            
            # Check for block before parsing
            if not res.candidates or not res.candidates[0].content.parts:
                st.error("🚫 Gemini blocked the output due to safety filters. Try a shorter clip or simpler scene.")
                st.stop()

            if "---NOVEL_START---" in res.text:
                parts = res.text.split("---NOVEL_START---")
                st.session_state.s_out = parts[0].replace("---SCRIPT_START---", "").strip()
                st.session_state.n_out = parts[1].strip()
                st.success("✅ Fusion Success!")
            else:
                st.warning("Could not split output. Raw text displayed below.")
                st.session_state.s_out = res.text
                st.session_state.n_out = "Fusion error—manual split required."

        except Exception as e:
            st.error(f"Fusion Crash: {e}")

# --- 7. OUTPUT & DOWNLOAD ---
if "n_out" in st.session_state:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Speaker-ID Transcript")
        st.text_area("V1", st.session_state.s_out, height=450)
    with r:
        st.subheader(f"📖 {pov_char}'s Novel Draft")
        st.text_area("V1", st.session_state.n_out, height=450)
    
    st.divider()
    # Word Doc Export
    final_doc = create_master_docx(st.session_state.s_out, st.session_state.n_out, pov_char)
    st.download_button(
        label="📥 Download Manuscript (.docx)",
        data=final_doc,
        file_name=f"Wizard_Archive_{pov_char}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
