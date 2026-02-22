import os
import streamlit as st
import tempfile
import time
import whisper
import subprocess
from google import genai
from google.genai import types

# --- 2026 CONFIG ---
MODEL_NAME = "gemini-3.1-pro-preview" 
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@st.cache_resource
def load_whisper():
    return whisper.load_model("turbo")

def extract_audio(video_path):
    audio_path = f"{video_path}_audio.mp3"
    subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-ac", "1", "-ar", "16000", "-b:a", "32k", audio_path, "-y"], capture_output=True)
    return audio_path

def process_production(uploaded_file, pov_character, show_name, episode_info, thinking_level):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
        tfile.write(uploaded_file.read())
        temp_video_path = tfile.name
    
    try:
        # 1. WHISPER (LINE-BY-LINE MODE)
        st.write("🎤 Transcribing line-by-line...")
        audio_path = extract_audio(temp_video_path)
        w_model = load_whisper()
        # Return segments for frame-by-frame accuracy
        result = w_model.transcribe(audio_path, verbose=False)
        transcript_lines = [f"[{round(s['start'], 1)}s] {s['text']}" for s in result['segments']]
        raw_transcript = "\n".join(transcript_lines)

        # 2. LORE GROUNDING
        st.write("🔍 Searching for Genie/Fashion Clues...")
        search_config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        research_response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=f"Recap '{show_name}' {episode_info}. Mention Billie's scuba suit and the Roman/Genie lamp theory clues.",
            config=search_config
        )
        lore = research_response.text

        # 3. VIDEO ANALYSIS
        st.write("☁️ Uploading Video...")
        video_file = client.files.upload(path=temp_video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)

        # 4. FINAL PRODUCTION
        st.write(f"✍️ Writing {pov_character}'s Novel & Detailed Script...")
        final_config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=65000,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if thinking_level != "OFF" else None
        )

        prompt = f"""LORE: {lore}
TRANSCRIPT: {raw_transcript[:10000]}
TASK:
1. [SCRIPT]: Create a line-by-line script. TAG EVERY CAMERA SHOT (e.g., [WIDE], [CU ROMAN]).
2. [NOVEL]: Write a 5,000+ word chapter from {pov_character}'s POV. 
   - Describe Billie's scuba suit and Roman's internal suspicion.
3. [GENIE_LOG]: Identify any 'Genie' clues (lamps, gold objects, Roman's magic glitches).
FORMAT: [SCRIPT]...[END_SCRIPT] [NOVEL]...[END_NOVEL] [GENIE_LOG]...[END_GENIE_LOG]"""

        response = client.models.generate_content(model=MODEL_NAME, contents=[prompt, video_file], config=final_config)
        full_text = response.text

        # 5. UI DISPLAY & PERSISTENCE
        st.subheader("🏁 Production Result")
        
        # SCRIPT TAB
        script = full_text.split("[SCRIPT]")[1].split("[END_SCRIPT]")[0].strip()
        novel = full_text.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
        genie = full_text.split("[GENIE_LOG]")[1].split("[END_GENIE_LOG]")[0].strip()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📜 Shot-by-Shot Script")
            st.text_area("Script Preview", script, height=300)
            st.download_button("💾 Download .txt Script", script, "script.txt")
        
        with col2:
            st.markdown(f"### 📖 {pov_character}'s Novel")
            st.text_area("Novel Preview", novel, height=300)
            st.download_button("💾 Download .txt Novel", novel, "novel.txt")

        st.info(f"🧞 Genie Theory Analysis:\n{genie}")

    finally:
        if os.path.exists(temp_video_path): os.remove(temp_video_path)

# --- UI ---
st.title("🎬 POV Cinematic Engine (Sync-Shot Edition)")
show = st.text_input("Show", "Wizards Beyond Waverly Place")
ep = st.text_input("Episode", "S01E03")
char = st.text_input("POV", "Roman")
lvl = st.select_slider("🧠 Reasoning", ["OFF", "LOW", "MEDIUM", "HIGH"], "MEDIUM")
up = st.file_uploader("Upload MP4", type=["mp4"])
if st.button("🚀 Start Production") and up:
    process_production(up, char, show, ep, lvl)
