import os
import streamlit as st
import tempfile
import time
import whisper
import subprocess
from google import genai
from google.genai import types

# --- 2026 FLAGSHIP CONFIG ---
MODEL_NAME = "gemini-3.1-pro-preview" 

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("🔑 Set API key: export GEMINI_API_KEY='your-key'")
    st.stop()

client = genai.Client(api_key=api_key)

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("turbo")

whisper_model = load_whisper_model()

def extract_audio(video_path):
    audio_path = f"{video_path}_audio.mp3"
    subprocess.run([
        "ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame",
        "-ac", "1", "-ar", "16000", "-b:a", "32k", audio_path, "-y"
    ], capture_output=True, check=True)
    return audio_path

def transcribe_with_whisper(audio_path):
    st.write("🎤 Transcribing with Whisper Turbo...")
    result = whisper_model.transcribe(audio_path, beam_size=1, temperature=0.0)
    return result['text']

def process_production(uploaded_file, pov_character, show_name, thinking_level):
    temp_video_path = None
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
            tfile.write(uploaded_file.read())
            temp_video_path = tfile.name
    
    try:
        # STEP 1: RESEARCH PHASE (Fixed Search Syntax)
        st.write(f"🔍 Grounding with Google Search...")
        search_config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        research_query = f"Provide a detailed plot recap for '{show_name}' Episode 3. Find specific subplots: Spelling Bee and Milo's outfits (scuba gear)."
        research_response = client.models.generate_content(
            model=MODEL_NAME, contents=research_query, config=search_config
        )
        lore_context = research_response.text

        with st.sidebar:
            st.success("✅ Context Grounded")
            with st.expander("👁️ Review Lore"):
                st.write(lore_context)

        # STEP 2: WHISPER TRANSCRIPTION
        audio_path = extract_audio(temp_video_path)
        transcript_text = transcribe_with_whisper(audio_path)
        
        # STEP 3: VIDEO UPLOAD (Argument Fix: 'file' instead of 'path')
        st.write("☁️ Uploading to Gemini 3.1 Pro...")
        video_file = client.files.upload(file=temp_video_path) # FIX: keyword is 'file'
        
        # Proper 2026 State Check
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            st.error("❌ Video processing failed on Google's side.")
            return

        st.success("✅ Video Active")

        # STEP 4: GENERATION (With Thinking Config)
        st.write(f"✍️ Writing {pov_character}'s Novel...")
        final_config = types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=65000,
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level 
            ) if thinking_level != "OFF" else None
        )

        prompt = f"""Use research: {lore_context}
**SITCOM RULES:** Visualize the 3D set. Ignore cuts.
**TRANSCRIPT:** {transcript_text[:8000]}
**TASK:** 1. Generate [SCRIPT]. 2. Write [NOVEL] from {pov_character}'s POV. 
Integrate the spelling bee stakes and Milo's scuba gear as found in the research.
**FORMAT:** [SCRIPT]...[END_SCRIPT] [NOVEL]...[END_NOVEL]"""

        response = client.models.generate_content(
            model=MODEL_NAME, contents=[prompt, video_file], config=final_config
        )
        
        # DISPLAY
        st.subheader("🏁 Production Complete")
        output = response.text
        if "[SCRIPT]" in output and "[NOVEL]" in output:
            script = output.split("[SCRIPT]")[1].split("[END_SCRIPT]")[0].strip()
            novel = output.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("Final Script", script, height=400)
                st.download_button("📥 Script", script, "script.txt")
            with c2:
                st.text_area("POV Novel", novel, height=400)
                st.download_button("📥 Novel", novel, f"{pov_character}_novel.txt")
        else:
            st.text_area("Full Output", output, height=500)

    except Exception as e:
        st.error(f"❌ Error: {e}")
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)

# --- UI ---
st.set_page_config(page_title="POV Engine 3.1", layout="wide")
st.title("🎬 POV Cinematic Engine")

with st.sidebar:
    st.header("⚙️ Settings")
    show_name = st.text_input("Show Name", "Wizards Beyond Waverly Place")
    pov_character = st.text_input("POV Character", "Roman")
    thinking_level = st.select_slider("🧠 Thinking Level", options=["OFF", "LOW", "MEDIUM", "HIGH"], value="MEDIUM")
    st.info(f"Model: {MODEL_NAME}")

uploaded = st.file_uploader("Upload Video", type=["mp4", "mov"])

if st.button("🚀 Start Production", type="primary"):
    if uploaded:
        process_production(uploaded, pov_character, show_name, thinking_level)
