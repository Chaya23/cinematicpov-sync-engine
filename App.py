import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import yt_dlp

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Fusion v16.9", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Check your Secrets for API keys!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. THE MULTI-DOWNLOADER (SCRIPT + NOVEL) ---
def create_master_docx(transcript, chapter, pov_name):
    """Creates a Word Doc with the full verbatim script followed by the novel."""
    doc = Document()
    doc.add_heading('OFFICIAL EPISODE ARCHIVE', 0)
    
    # Transcript Section
    doc.add_heading('Verbatim Speaker-Identified Transcript', level=1)
    doc.add_paragraph(transcript)
    
    doc.add_page_break()
    
    # Novel Section
    doc.add_heading(f'Chapter Novelization: {pov_name}\'s POV', level=1)
    doc.add_paragraph(chapter)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. CORE ENGINES ---
def download_video(url, tmp_dir):
    """Bypasses blocks on YouTube/Disney/Solar by spoofing a browser."""
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

def get_model():
    """Finds the current working Gemini Flash ID to avoid 404s."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((m for m in models if "flash" in m), "gemini-1.5-flash")
    except: return "gemini-1.5-flash"

# --- 4. THE STUDIO UI ---
with st.sidebar:
    st.header("🎭 Character Manager")
    cast_names = st.text_area("Cast Members:", "Roman, Billie, Justin, Winter, Milo, Giada")
    pov_char = st.selectbox("POV for Novel:", [c.strip() for c in cast_names.split(",")])
    st.divider()
    st.info("v16.9: Full Speaker Attribution + Word Export")

st.title("🎬 CinematicPOV Fusion v16.9")
url = st.text_input("Enter Episode URL (DisneyNow, SolarMovie, YouTube):")
upload = st.file_uploader("OR Upload Video File:", type=['mp4', 'webm', 'mkv'])

if st.button("🚀 EXECUTE FULL FUSION", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Acquisition
        v_path = ""
        if upload:
            v_path = os.path.join(tmp_dir, upload.name)
            with open(v_path, "wb") as f: f.write(upload.getbuffer())
        else:
            st.info("🕵️ Accessing Video Source...")
            v_path = download_video(url, tmp_dir)

        if not v_path:
            st.error("Could not reach video. Please upload the file directly.")
            st.stop()

        # Step 1: Whisper (Accurate Text)
        st.info("👂 Whisper: Transcribing every word...")
        audio = os.path.join(tmp_dir, "a.mp3")
        subprocess.run(f"ffmpeg -i '{v_path}' -ar 16000 -ac 1 -map a '{audio}' -y", shell=True, capture_output=True)
        with open(audio, "rb") as f_a:
            raw_t = client_oa.audio.transcriptions.create(model="whisper-1", file=f_a, response_format="text")

        # Step 2: Gemini Vision (Speaker Identification)
        st.info("☁️ Gemini: Watching for Speaker ID...")
        vf = genai.upload_file(path=v_path)
        while vf.state.name == "PROCESSING": time.sleep(2); vf = genai.get_file(vf.name)

        # Step 3: The Fusion
        st.info(f"✍️ Syncing Transcript & Writing {pov_char}'s POV...")
        model = genai.GenerativeModel(get_model())
        prompt = f"""
        TRANSCRIPT: {raw_t}
        CAST: {cast_names}
        
        TASK:
        1. LINE-BY-LINE SCRIPT: Identify the speaker for every single line of the transcript. Format as [NAME]: [Dialogue].
        2. NOVEL CHAPTER: Write a YA chapter from {pov_char}'s POV. 
           Include his deep internal thoughts and reactions to what others are saying. 
           Stick to the exact dialogue provided in the transcript.
        
        FORMAT:
        ---SCRIPT_START---
        [Complete Speaker Script]
        ---NOVEL_START---
        [Full Chapter]
        """
        res = model.generate_content([vf, prompt])
        genai.delete_file(vf.name)

        if "---NOVEL_START---" in res.text:
            parts = res.text.split("---NOVEL_START---")
            st.session_state.final_script = parts[0].replace("---SCRIPT_START---", "").strip()
            st.session_state.final_novel = parts[1].strip()
            st.success("✅ Fusion Complete!")

# --- 5. EXPORT & DOWNLOAD ---
if "final_novel" in st.session_state:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📝 Verbatim Script (Speaker-ID)")
        st.text_area("Transcript", st.session_state.final_script, height=450)
    with c2:
        st.subheader(f"📖 {pov_char}'s Novel Chapter")
        st.text_area("Manuscript", st.session_state.final_novel, height=450)
    
    st.divider()
    # Word Export
    master_file = create_master_docx(st.session_state.final_script, st.session_state.final_novel, pov_char)
    st.download_button(
        label="📥 Download Full Archive (.docx)",
        data=master_file,
        file_name=f"Wizard_Archive_{pov_char}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
