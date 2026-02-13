  import streamlit as st
import os, tempfile
from openai import OpenAI
import google.generativeai as genai
import yt_dlp
from pydub import AudioSegment

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="CinematicPOV Sync v10.5", layout="wide", page_icon="🎬")

# Load Keys from Secrets
try:
    openai_key = st.secrets["OPENAI_API_KEY"]
    google_key = st.secrets["GOOGLE_API_KEY"]
    proxy_url = st.secrets.get("PROXY_URL") # Add your proxy here in Streamlit Secrets
except KeyError:
    st.error("API Keys missing in Streamlit Secrets!")
    st.stop()

client = OpenAI(api_key=openai_key)
genai.configure(api_key=google_key)

# --- 2. TRANSCRIPTION ENGINE (Handles 413 Error & Full Episodes) ---
def get_transcript(file_path):
    audio = AudioSegment.from_file(file_path)
    chunk_ms = 5 * 60 * 1000  # 5-minute chunks
    full_text = ""
    
    progress_text = st.empty()
    bar = st.progress(0)
    chunks = range(0, len(audio), chunk_ms)
    
    for i, start in enumerate(chunks):
        progress_text.text(f"🎤 Processing Audio Chunk {i+1} of {len(chunks)}...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            # Bitrate 64k keeps file size tiny for OpenAI's 25MB limit
            audio[start:start+chunk_ms].export(tmp.name, format="mp3", bitrate="64k")
            with open(tmp.name, "rb") as f:
                response = client.audio.transcriptions.create(model="whisper-1", file=f)
                full_text += response.text + " "
            os.unlink(tmp.name)
        bar.progress((i + 1) / len(chunks))
    
    progress_text.text("✅ Transcription Complete!")
    return full_text

# --- 3. THE "NUCLEAR" BYPASS DOWNLOADER ---
def download_stealth(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "audio.%(ext)s")
    
    # Check for local cookies file
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_path,
        'quiet': True,
        'proxy': proxy_url,  # THIS FIXES THE BLOCK
        'geo_bypass': True,
        'cookiefile': cookie_path,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://disneynow.com/',
        },
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "audio.mp3")

# --- 4. MAIN INTERFACE ---
st.title("🎬 CinematicPOV Sync Engine v10.5")
st.info("Bypassing IP blocks and grounding with LaughingPlace recaps.")

col1, col2 = st.columns(2)
with col1:
    url_input = st.text_input("Paste Link (YouTube/Disney/Solar):")
    uploaded = st.file_uploader("OR Upload Full Episode Audio:", type=['mp3', 'mp4', 'm4a'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select Character POV:", chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Enter Character Name:")

if st.button("🔥 START FULL SYNC", type="primary"):
    if not url_input and not uploaded:
        st.warning("Please provide a source!")
        st.stop()

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step 1: Get Audio
            with st.spinner("Downloading/Loading Audio..."):
                if uploaded:
                    path = os.path.join(tmp_dir, "input.mp3")
                    with open(path, "wb") as f: f.write(uploaded.getbuffer())
                else:
                    path = download_stealth(url_input, tmp_dir)

            # Step 2: Transcribe
            full_raw_text = get_transcript(path)
            
            # Step 3: AI Processing with Grounding
            st.spinner("🧠 Analyzing Characters & Writing POV...")
            model = genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-2.5-flash' if available in your region
            
            prompt = f"""
            You are a creative writer and 'Wizards Beyond Waverly Place' expert.
            
            CONTEXT: Use your internal search knowledge of 'LaughingPlace' recaps for this show.
            FACTS: Roman made the 'Lacey' vase. Milo wants the monkey. Billie gets the Staten Island makeover. 
            The theme song and plot must match exactly.
            
            TRANSCRIPT: {full_raw_text}
            
            TASK:
            1. Create a FULL Labeled Transcript (Character: "Dialogue").
            2. Write a detailed first-person POV novel chapter for {pov_char} covering the whole episode.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Labeled Transcript]
            ---POV_START---
            [Novel Chapter]
            """
            
            res = model.generate_content(prompt)
            output_text = res.text
            
            # Parsing Results
            if "---POV_START---" in output_text:
                parts = output_text.split("---POV_START---")
                st.session_state.labeled = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.story = parts[1]
            else:
                st.session_state.story = output_text
                st.session_state.labeled = "AI failed to split transcript. Check full result below."
            
            st.success("✅ Sync Successful!")

        except Exception as e:
            st.error(f"DOWNLOAD ERROR: Disney/Solar is still blocking. {e}")
            st.info("💡 FIX: Use a residential proxy in Secrets or upload the file manually.")

# --- 5. RESULTS ---
t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])

if "story" in st.session_state:
    with t1:
        st.markdown(f"## {pov_char}'s Story")
        st.write(st.session_state.story)
        st.download_button("Download Story", st.session_state.story, "story.txt")
    with t2:
        st.text_area("Full Labeled Transcript (Copy-Paste):", st.session_state.labeled, height=500)
          
