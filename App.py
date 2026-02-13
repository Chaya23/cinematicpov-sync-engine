import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="CinematicPOV: Auto-Link v13.2", layout="wide", page_icon="✍️")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE MODEL FINDER (The 404 Fix) ---
def get_best_model():
    """Scans for available Flash models to prevent 404 errors."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioritize Flash models for speed/video
        flash_models = [m for m in models if 'flash' in m.lower()]
        if flash_models:
            return flash_models[0].split('/')[-1] # Returns just the ID
        return "gemini-1.5-flash" # Fallback
    except:
        return "gemini-1.5-flash"

# --- 3. VIDEO OPTIMIZER ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 4. STUDIO INTERFACE ---
st.title("✍️ CinematicPOV: Verified Studio v13.2")
st.caption("Auto-Detecting Models • Side-by-Side Accuracy")

with st.expander("⚙️ Episode & Style Settings", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        url_input = st.text_input("Source URL (DisneyNow/YouTube/Solar):")
        uploaded = st.file_uploader("Upload Video:", type=['mp4'])
    with col2:
        pov_char = st.selectbox("POV Character:", ["Roman", "Billie", "Justin", "Winter", "Milo"])
        style = st.selectbox("Narrative Style:", ["YA Novel (Sarah J. Maas)", "Middle Grade (Percy Jackson)"])

if st.button("🚀 SYNC & AUTHOR", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading episode video...")
                video_path = download_video(url_input, tmp_dir)

            st.info("☁️ Vision Engine analyzing speakers...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            # --- THE FIX: GET THE CORRECT MODEL NAME ---
            target_model = get_best_model()
            st.caption(f"Connected to Engine: {target_model}")
            model = genai.GenerativeModel(target_model)
            
            prompt = f"""
            Identify all characters visually. Match every line of spoken dialogue to the correct name.
            
            1. FULL TRANSCRIPT:
            - Format: [MM:SS] Name: "Dialogue"
            - Include every single word spoken.
            
            2. NOVEL CHAPTER:
            - Write a detailed first-person chapter for {pov_char}.
            - ACCURACY: Ensure every key line from the transcript is woven into the story.
            - Style: {style}.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Insert Time-Stamped Script]
            ---POV_START---
            [Insert Novel]
            """

            # Generation with high token allowance
            response = model.generate_content(
                [video_file, prompt],
                generation_config={"max_output_tokens": 8192, "temperature": 0.4}
            )
            
            if response and response.text:
                parts = response.text.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Studio View Ready!")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. SIDE-BY-SIDE STUDIO ---
if "transcript" in st.session_state:
    st.divider()
    left, right = st.columns(2)
    
    with left:
        st.subheader("🎤 Verified Transcript")
        st.text_area("Source Dialogue", st.session_state.transcript, height=800, label_visibility="collapsed")
        
    with right:
        st.subheader(f"📖 {pov_char}'s Adaptation")
        st.text_area("Novelized Story", st.session_state.novel, height=800, label_visibility="collapsed")
