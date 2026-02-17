import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from io import BytesIO
from docx import Document

# ---------------- 1. SETUP & CONFIG ----------------
st.set_page_config(page_title="Fanfic POV Engine", layout="wide")

# API Key Check
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("🔑 API Key missing. Add it to Streamlit Secrets as GEMINI_API_KEY.")
    st.stop()

genai.configure(api_key=api_key)

# --- MODEL DIAGNOSTICS ---
def list_available_models():
    """Lists all models your specific API key can access."""
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        return available
    except Exception as e:
        return [f"Error listing models: {str(e)}"]

# Persistent State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# ---------------- 2. SIDEBAR ----------------
with st.sidebar:
    st.title("🛠️ Debug Tools")
    if st.checkbox("Show Supported API Models"):
        models = list_available_models()
        st.write(models)
    
    st.divider()
    st.header("🎭 Character Bible")
    default_cast = "Roman: Protagonist\nGiada: Mother\nJustin: Father\nBillie: Sister\nMilo: Brother\nWinter: Friend"
    cast_info = st.text_area("Cast List (name: role):", default_cast, height=150)
    
    cast_names = [line.split(":")[0].strip() for line in cast_info.split("\n") if ":" in line]
    pov_choice = st.selectbox("Narrator POV:", ["Roman"] + [n for n in cast_names if n != "Roman"])

# ---------------- 3. MAIN INTERFACE ----------------
st.title("📚 Fanfic POV Engine")
st.caption("Generate scripts and novel chapters from video.")

tab_up, tab_url = st.tabs(["📁 Local Video Upload", "🌐 Streaming URL Sync"])

with tab_up:
    file_vid = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])
with tab_url:
    url_link = st.text_input("Paste Video URL:")

# ---------------- 4. PRODUCTION ENGINE ----------------
if st.button("🚀 START PRODUCTION", use_container_width=True):
    with st.status("🎬 Processing...") as status:
        source = "temp_video.mp4"
        try:
            # 4.1. Handle Video
            if file_vid:
                with open(source, "wb") as f: f.write(file_vid.getbuffer())
            elif url_link:
                status.update(label="⬇️ Downloading...", state="running")
                subprocess.run(["yt-dlp", "-f", "best[ext=mp4]", "-o", source, url_link], check=True)

            # 4.2. Upload to Gemini
            status.update(label="📤 Uploading to AI...", state="running")
            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(2)
                gem_file = genai.get_file(gem_file.name)

            # 4.3. Model Selection (Auto-pick the best Flash model)
            supported = list_available_models()
            # We want 'gemini-1.5-flash' or 'gemini-2.0-flash' or 'gemini-3-flash'
            # This logic picks the first one found in your key's list
            best_model = next((m for m in supported if "flash" in m), supported[0])
            
            model = genai.GenerativeModel(best_model)
            
            # 4.4. Prompt
            prompt = f"POV: {pov_choice}. CAST: {cast_info}. \nTASK 1: Full transcript with names. \n---SPLIT---\nTASK 2: First-person novel chapter."

            # 4.5. Generate
            status.update(label=f"🧠 Writing with {best_model}...", state="running")
            response = model.generate_content([gem_file, prompt])

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip()
                st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if os.path.exists(source): os.remove(source)

# ---------------- 5. RESULTS ----------------
if st.session_state.transcript:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Transcript")
        st.text_area("T-Box", st.session_state.transcript, height=500)
    with col2:
        st.subheader(f"📖 {pov_choice}'s Chapter")
        st.text_area("N-Box", st.session_state.chapter, height=500)
