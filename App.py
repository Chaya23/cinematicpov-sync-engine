import os
import streamlit as st
import tempfile
import time
import whisper
import gc  # Garbage Collector to free RAM
import subprocess
from google import genai
from google.genai import types

# --- MOBILE STABILITY CONFIG ---
MODEL_NAME = "gemini-3.1-pro-preview" 
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Use Session State to keep data if the mobile browser refreshes
for key in ["script", "novel", "processing"]:
    if key not in st.session_state:
        st.session_state[key] = None

@st.cache_resource
def load_whisper_mobile():
    # Use "base" or "tiny" for low-end phones, "turbo" only if server-side
    return whisper.load_model("base") 

def clear_memory():
    """Forcefully clear RAM after heavy tasks."""
    gc.collect()

def extract_audio_mobile(video_path):
    audio_path = f"{video_path}_low.mp3"
    # Convert to ultra-low bitrate to save mobile memory
    subprocess.run([
        "ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame",
        "-ac", "1", "-ar", "16000", "-b:a", "24k", audio_path, "-y"
    ], capture_output=True)
    return audio_path

def run_production_mobile(uploaded_file, pov_char, show, title):
    # Save file to disk immediately (don't keep in RAM)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
        tfile.write(uploaded_file.getbuffer())
        video_path = tfile.name
    
    try:
        # STEP 1: Search (Title Precision)
        search_cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        res = client.models.generate_content(
            model=MODEL_NAME, 
            contents=f"Detailed plot/fashion recap for '{show}' episode '{title}'",
            config=search_cfg
        )
        lore = res.text
        
        # STEP 2: Audio (Mobile Optimized)
        audio_path = extract_audio_mobile(video_path)
        w_model = load_whisper_mobile()
        segments = w_model.transcribe(audio_path)["segments"]
        transcript = "\n".join([f"[{s['start']}s] {s['text']}" for s in segments])
        
        # Free Whisper RAM immediately
        del w_model
        clear_memory()

        # STEP 3: Video Analysis
        file_ref = client.files.upload(path=video_path)
        while file_ref.state.name == "PROCESSING":
            time.sleep(3)
            file_ref = client.files.get(name=file_ref.name)

        # STEP 4: Novel Writing
        prompt = f"RECAP: {lore}\nTRANSCRIPT: {transcript}\nTASK: [SCRIPT] line-by-line script. [NOVEL] {pov_char} POV chapter."
        final_res = client.models.generate_content(model=MODEL_NAME, contents=[prompt, file_ref])
        
        # Save to session so it survives a page flicker
        st.session_state.script = final_res.text.split("[SCRIPT]")[1].split("[END_SCRIPT]")[0]
        st.session_state.novel = final_res.text.split("[NOVEL]")[1].split("[END_NOVEL]")[0]

    finally:
        # Crucial for mobile: Delete files from the server disk after use
        if os.path.exists(video_path): os.remove(video_path)
        if 'audio_path' in locals() and os.path.exists(audio_path): os.remove(audio_path)
        clear_memory()

# --- MOBILE UI LAYOUT ---
st.set_page_config(page_title="Mobile POV Engine", layout="centered") # Centered is better for phones
st.title("🎬 POV Engine Mobile")

# Use an Expander for settings to save screen space
with st.expander("⚙️ Episode Settings", expanded=True):
    show = st.text_input("Show", "Wizards Beyond Waverly Place")
    title = st.text_input("Episode Title", "S01E03")
    pov = st.text_input("POV Character", "Roman")

up = st.file_uploader("Upload Video", type=["mp4"])

if st.button("🚀 Start Production (Mobile Safe)"):
    if up:
        with st.status("Processing... This may take a minute on mobile."):
            run_production_mobile(up, pov, show, title)
        st.rerun()

# --- PERSISTENT RESULTS DISPLAY ---
if st.session_state.script:
    st.divider()
    # Using tabs for mobile so you don't have to scroll forever
    tab1, tab2 = st.tabs(["📜 Script", "📖 Novel"])
    
    with tab1:
        st.text_area("Final Transcript", st.session_state.script, height=300)
        st.download_button("📥 Save Script", st.session_state.script, f"{title}_script.txt")
        
    with tab2:
        st.text_area("POV Novel", st.session_state.novel, height=300)
        st.download_button("📥 Save Novel", st.session_state.novel, f"{pov}_novel.txt")
