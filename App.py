          import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Sync v9.6", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. TRANSCRIPTION ENGINE ---
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

# --- 3. THE RE-FIXED DOWNLOADER ---
def download_with_bypass(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "a.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'noplaylist': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        # AGGRESSIVE BYPASS HEADERS
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "a.mp3")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v9.6")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Paste Link:")
    uploaded = st.file_uploader("OR Upload Audio File:", type=['mp3', 'mp4', 'm4a'])
with col2:
    standard_chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select POV:", standard_chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Name:")

if st.button("🔥 RUN SYNC", type="primary"):
    if not url_input and not uploaded:
        st.error("Please provide a link or file.")
        st.stop()

    with st.spinner("Bypassing site security & extracting audio..."):
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                if uploaded:
                    path = os.path.join(tmp_dir, "input.mp3")
                    with open(path, "wb") as f: f.write(uploaded.getbuffer())
                else:
                    path = download_with_bypass(url_input, tmp_dir)

                # Step 2: Transcribe
                st.text("🎤 Transcribing...")
                raw_text = get_transcript(path)
                
                # Step 3: Grounding & Novel
                st.text(f"🧠 Grounding with Wiki & Writing {pov_char} POV...")
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                master_prompt = f"""
                You are a story engine. Use web search to match this transcript to the correct episode of 'Wizards Beyond Waverly Place'.
                TRANSCRIPT: {raw_text[:2500]}
                
                1. Label speakers accurately (e.g. Billie: [Dialogue], Roman: [Dialogue]). 
                   NOTE: Billie gets the Staten Island makeover. Milo wants the monkey. Roman/Winter do the friendship spell.
                2. Write a 1st person POV chapter for {pov_char}.
                
                FORMAT:
                ---TRANSCRIPT---
                [Labeled Transcript]
                ---POV---
                [Novel Chapter]
                """
                
                res = model.generate_content(master_prompt)
                full_text = res.text
                
                if "---POV---" in full_text:
                    parts = full_text.split("---POV---")
                    st.session_state.labeled = parts[0].replace("---TRANSCRIPT---", "")
                    st.session_state.story = parts[1]
                else:
                    st.session_state.story = full_text
                
                st.success("Sync Complete!")

            except Exception as e:
                st.error(f"Download failed. The site is blocking the server. Try downloading the audio to your phone and uploading it here. Error: {e}")

# --- 5. TABS ---
t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])
if "story" in st.session_state:
    with t1:
        st.write(st.session_state.story)
        st.download_button("Download Story", st.session_state.story, "story.txt")
    with t2:
        st.text_area("Labeled Transcript:", st.session_state.labeled if "labeled" in st.session_state else "Processing...", height=400)
  
