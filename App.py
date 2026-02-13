import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Sync v10.0", layout="wide")

# API Keys
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE TRANSCRIPTION ENGINE (Full 23-Min Support) ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_ms = 5 * 60 * 1000 # 5-minute chunks
    full_text = ""
    progress_bar = st.progress(0)
    total_chunks = len(range(0, len(audio), chunk_ms))
    
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            # Export chunk
            audio[start:start+chunk_ms].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
            progress_bar.progress((i + 1) / total_chunks)
    return full_text

# --- 3. DOWNLOADER (Stealth Mode) ---
def download_audio(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "audio.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
        },
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "audio.mp3")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Sync Engine v10.0")
st.caption("Now supporting full 23-minute episodes with LaughingPlace grounding.")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Link (YouTube/Disney/Solar):")
    uploaded = st.file_uploader("OR Upload Full Episode File:", type=['mp3', 'mp4', 'm4a'])
with col2:
    standard_chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select Character POV:", standard_chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Type Name:")

if st.button("🚀 RUN FULL SYNC", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # 1. Get Audio
            path = download_audio(url_input, tmp_dir) if not uploaded else os.path.join(tmp_dir, "in.mp3")
            if uploaded:
                with open(path, "wb") as f: f.write(uploaded.getbuffer())

            # 2. Full Transcription
            st.info("🎤 Transcribing Full Episode (23 mins)... Please wait.")
            full_raw_text = get_transcript(path)
            
            # 3. AI Grounding & Processing
            st.info("🧠 Syncing with LaughingPlace Recaps & Mapping Characters...")
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # THE MASTER PROMPT (No more slicing!)
            master_prompt = f"""
            SYSTEM: You are an expert on 'Wizards Beyond Waverly Place'. 
            CONTEXT: Ground your response in the LaughingPlace recaps for Season 2 Episode 2 and Season 1 Episode 2.
            FACTS: 
            - Roman made the 'Lacey' vase for Mom.
            - Billie gets the Staten Island makeover.
            - Milo applied for a pet monkey.
            - The 'Back Together' spell is: "Mend the cracks now and forever, bring it all right back together."
            
            TRANSCRIPT: {full_raw_text}
            
            TASK:
            1. Provide a FULL, accurate transcript with names next to every line.
            2. Write a 1st-person POV novel chapter for {pov_char} covering the whole episode plot.
            
            FORMAT:
            ---LABELED_TRANSCRIPT---
            [Name: Dialogue]
            ---CHARACTER_POV---
            [Story]
            """
            
            res = model.generate_content(master_prompt)
            output = res.text
            
            # Split and Save
            if "---CHARACTER_POV---" in output:
                t_part, s_part = output.split("---CHARACTER_POV---")
                st.session_state.full_labeled = t_part.replace("---LABELED_TRANSCRIPT---", "")
                st.session_state.full_story = s_part
                st.success("✅ FULL EPISODE SYNCED!")
            else:
                st.session_state.full_story = output

        except Exception as e:
            st.error(f"Sync failed: {e}")

# --- 5. TABS ---
t1, t2 = st.tabs(["📖 Full Character Novel", "📝 Full Labeled Transcript"])

if "full_story" in st.session_state:
    with t1:
        st.markdown(f"### {pov_char}'s Story")
        st.write(st.session_state.full_story)
        st.download_button("Download Story", st.session_state.full_story, f"{pov_char}_full_story.txt")
    with t2:
        st.markdown("### Accurate Labeled Transcript")
        # Use text_area for easy copy-pasting of long texts
        st.text_area("Full Transcript (Verified):", st.session_state.full_labeled, height=600)
