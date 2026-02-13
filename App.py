import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Sync v9.5", layout="wide")

# API Keys
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. TRANSCRIPTION ENGINE (Handles 413 error) ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_length = 5 * 60 * 1000 
    chunks = range(0, len(audio), chunk_length)
    full_text = ""
    for i, start in enumerate(chunks):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio[start:start+chunk_length].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
    return full_text

# --- 3. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v9.5")
st.caption("AI-Powered Diarization & Plot Grounding")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Paste Link (YouTube/Disney/Solar):")
    uploaded = st.file_uploader("OR Upload Audio File:", type=['mp3', 'mp4', 'm4a'])
with col2:
    standard_chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select Character POV:", standard_chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Type Character Name:")

if st.button("🔥 RUN SYNC & LABEL", type="primary"):
    with st.spinner("Step 1: Extracting Audio & Bypassing Blocks..."):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = None
            if uploaded:
                path = os.path.join(tmp_dir, "input.mp3")
                with open(path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                ydl_opts = {
                    'format': 'bestaudio',
                    'outtmpl': os.path.join(tmp_dir, "a.%(ext)s"),
                    'geo_bypass': True,
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url_input])
                path = os.path.join(tmp_dir, "a.mp3")

            # --- STEP 2: TRANSCRIBE ---
            st.spinner("Step 2: Transcribing Audio (Whisper)...")
            raw_text = get_transcript(path)
            
            # --- STEP 3: PLOT MATCHING & DIARIZATION ---
            st.spinner("Step 3: Grounding with Plot & Labeling Speakers...")
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # This prompt forces accuracy by checking real show facts
            master_prompt = f"""
            SYSTEM TASK:
            1. Search the web for 'Wizards Beyond Waverly Place' episode plots to match this transcript: {raw_text[:2000]}
            2. Identify the EXACT episode.
            3. DIARIZATION: Rewrite the full transcript below, placing the speaker's name before every line (e.g., Billie: "...", Roman: "..."). 
               Be careful: Milo wanted the pet monkey, Billie got the Staten Island makeover, Roman and Winter got stuck together.
            4. NOVEL: Write a high-quality 1st-person POV chapter for {pov_char} based on the labeled transcript.
            
            FORMAT:
            ---TRANSCRIPT---
            [Labeled Transcript Here]
            
            ---POV_CHAPTER---
            [POV Chapter Here]
            """
            
            try:
                res = model.generate_content(master_prompt)
                full_response = res.text
                
                # Split for UI
                if "---POV_CHAPTER---" in full_response:
                    transcript_part, pov_part = full_response.split("---POV_CHAPTER---")
                    st.session_state.labeled_transcript = transcript_part.replace("---TRANSCRIPT---", "")
                    st.session_state.final_pov = pov_part
                else:
                    st.session_state.final_output = full_response
                
                st.success("Sync Complete!")
            except Exception as e:
                st.error(f"AI Error: {e}")

# --- 4. RESULTS DISPLAY ---
t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])

if "final_pov" in st.session_state:
    with t1:
        st.markdown(f"### {pov_char}'s Perspective")
        st.write(st.session_state.final_pov)
        st.download_button("Download POV", st.session_state.final_pov, f"{pov_char}_POV.txt")
    with t2:
        st.markdown("### Official Labeled Transcript")
        st.text_area("Copy this for your notes:", st.session_state.labeled_transcript, height=400)
