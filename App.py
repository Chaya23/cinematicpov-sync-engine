import os
import streamlit as st
import tempfile
import time
import whisper
import subprocess
from google import genai
from google.genai import types

# --- 2026 SDK SETUP ---
MODEL_NAME = "gemini-3.1-pro-preview" 
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Persistent Memory for UI
if "final_script" not in st.session_state: st.session_state.final_script = None
if "final_novel" not in st.session_state: st.session_state.final_novel = None

@st.cache_resource
def load_whisper():
    return whisper.load_model("turbo")

def process_production(uploaded_file, pov_char, show_name, exact_title):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
        tfile.write(uploaded_file.read())
        video_path = tfile.name
    
    try:
        # 1. GROUNDING: Fetch the REAL plot for the typed title
        st.write(f"🔍 Searching official recaps for: {exact_title}...")
        search_cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        # Force search to find the typed title specifically
        grounding_prompt = f"Provide the official plot recap and fashion details for '{show_name}' episode titled '{exact_title}'."
        res = client.models.generate_content(model=MODEL_NAME, contents=grounding_prompt, config=search_cfg)
        official_lore = res.text

        # 2. TRANSCRIPTION: Whisper Line-by-Line
        st.write("🎤 Transcribing Audio...")
        audio_path = f"{video_path}.mp3"
        subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-y", audio_path], capture_output=True)
        w_model = load_whisper()
        segments = w_model.transcribe(audio_path)["segments"]
        transcript = "\n".join([f"[{s['start']}s] {s['text']}" for s in segments])

        # 3. VIDEO ANALYSIS: Gemini watches with the Lore in mind
        st.write("☁️ Uploading Video...")
        file_ref = client.files.upload(path=video_path)
        while file_ref.state.name == "PROCESSING": time.sleep(4); file_ref = client.files.get(name=file_ref.name)

        # 4. WRITING: Combine Search Data + Video Frames + Transcript
        st.write("✍️ Generating Accurate Script & Novel...")
        prompt = f"""
        OFFICIAL RECAP (SEARCHED): {official_lore}
        TRANSCRIPT: {transcript}
        TASK:
        1. [SCRIPT]: Create a line-by-line script using the timestamps. Tag camera shots.
        2. [NOVEL]: Write a chapter in {pov_char}'s POV. MUST follow the RECAP facts (outfits, plot).
        FORMAT: [SCRIPT]...[END_SCRIPT] [NOVEL]...[END_NOVEL]
        """
        final_res = client.models.generate_content(model=MODEL_NAME, contents=[prompt, file_ref])
        
        # Save to session memory
        st.session_state.final_script = final_res.text.split("[SCRIPT]")[1].split("[END_SCRIPT]")[0]
        st.session_state.final_novel = final_res.text.split("[NOVEL]")[1].split("[END_NOVEL]")[0]

    finally:
        if os.path.exists(video_path): os.remove(video_path)

# --- UI ---
st.title("🎬 POV Engine: Precision Mode")
with st.sidebar:
    show = st.text_input("Show", "Wizards Beyond Waverly Place")
    title = st.text_input("EXACT Episode Title", "The Legend of Creepy Follows")
    pov = st.text_input("POV Character", "Roman")

up = st.file_uploader("Upload MP4")
if st.button("🚀 Run Production") and up:
    process_production(up, pov, show, title)

if st.session_state.final_script:
    st.markdown("### ✅ Results Ready")
    c1, c2 = st.columns(2)
    with c1:
        st.text_area("Script", st.session_state.final_script, height=400)
        st.download_button("📥 Download Script", st.session_state.final_script, "script.txt")
    with c2:
        st.text_area("Novel", st.session_state.final_novel, height=400)
        st.download_button("📥 Download Novel", st.session_state.final_novel, "novel.txt")
