 import streamlit as st
import os, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import yt_dlp

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Roman's Justice v20.0", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea { background-color: #1e1e1e; color: #00ff00; font-family: 'Courier New'; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS ---
# Input keys manually in the sidebar for local security
with st.sidebar:
    st.header("🔑 Wizard Keys")
    GEMINI_KEY = st.text_input("Gemini API Key:", type="password")
    OPENAI_KEY = st.text_input("OpenAI API Key:", type="password")
    st.divider()
    st.info("Ensure 'cookies.txt' is in the script folder for Disney/Solar bypass.")

if GEMINI_KEY and OPENAI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    client_oa = OpenAI(api_key=OPENAI_KEY)

# --- 3. THE STEALTH ENGINE ---
def stealth_download(url):
    st.info("🛰️ Bypassing Geoblocks & DRM via Cookies...")
    out_name = "episode_3_capture.mp4"
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best',
        'outtmpl': out_name,
        'cookiefile': 'cookies.txt', # Matches your local file
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return out_name

# --- 4. THE UI ---
st.title("🧙 Wizards Beyond: The Roman Redemption")
st.caption("Target: Season 1, Episode 3 - 'Saved by the Spell'")

col_vid, col_txt = st.columns(2)

with col_vid:
    video_url = st.text_input("Enter Video Link (Solar/VidCloud/Disney):")
    
with col_txt:
    st.write("📄 Forever Dreaming Transcript detected in memory.")
    # We use the text you provided in the prompt
    transcript_content = st.text_area("Transcript Content:", value="[PASTED TRANSCRIPT FROM YOUR PROMPT]", height=200)

if st.button("🚀 EXECUTE SYNCED ANALYSIS"):
    if not (GEMINI_KEY and OPENAI_KEY):
        st.error("Please enter both API keys in the sidebar.")
    else:
        # STEP 1: DOWNLOAD
        v_file = stealth_download(video_url)
        
        # STEP 2: WHISPER AUDIO EXTRACT
        st.info("👂 Whisper is listening for Roman's 'Sidelined' moments...")
        audio_path = "temp_voice.mp3"
        subprocess.run(f"ffmpeg -i {v_file} -q:a 0 -map a {audio_path} -y", shell=True)
        
        with open(audio_path, "rb") as f:
            transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            verbatim_text = transcription.text

        # STEP 3: GEMINI VISUAL SYNC
        st.info("👁️ Gemini is watching the video to find the bias...")
        video_ai = genai.upload_file(path=v_file)
        while video_ai.state.name == "PROCESSING":
            time.sleep(2)
            video_ai = genai.get_file(video_ai.name)

        # STEP 4: JUSTICE PROMPT (The "Roman Russo" Special)
        prompt = f"""
        You are a novel writer specializing in fixing character bias.
        
        INPUT DATA:
        1. Transcript (Truth): {transcript_content}
        2. Audio (Whisper): {verbatim_text}
        3. Video: Provided file.
        
        DIRECTIONS:
        - Match the 'Forever Dreaming' transcript names to the video faces.
        - Identify every time Roman is ignored (e.g., when Winter is 'stolen' or Justin dismisses him).
        - Write a NOVEL CHAPTER from ROMAN'S POV for Episode 3.
        - Show Roman's internal logic: He knows the Phantomus is dangerous while everyone else is playing.
        - ENDING: Write a 'Tribunal Teaser' where Roman's discipline is noted by the High Wizards.
        
        OUTPUT FORMAT:
        ## NOVEL: ROMAN'S PERSPECTIVE
        [The Chapter]
        ---
        ## SYNCED SCRIPT
        [Speaker Names: Dialogue]
        """

        model = genai.GenerativeModel("gemini-1.5-flash")
        result = model.generate_content([video_ai, prompt])

        # --- DISPLAY RESULTS ---
        st.markdown(result.text)
        
        # Word Doc Export
        doc = Document()
        doc.add_heading("Wizards Beyond: The Roman Russo Record", 0)
        doc.add_paragraph(result.text)
        buffer = BytesIO()
        doc.save(buffer)
        st.download_button("📥 Download Novel Archive", buffer.getvalue(), "Roman_Justice_Ep3.docx")
        
        # Clean up
        genai.delete_file(video_ai.name)
                   
