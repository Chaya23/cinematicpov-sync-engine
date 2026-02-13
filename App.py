import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV: Unbreakable v12.5", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY. Add it to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. QUOTA-SAFE RETRY LOGIC ---
def safe_generate(model, content, max_retries=3):
    """Retries generation if Quota (429) is hit."""
    for attempt in range(max_retries):
        try:
            # We use a standard generation config without 'tools' to prevent crashes
            return model.generate_content(
                content, 
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 8192 # Max length for full scripts
                }
            )
        except exceptions.ResourceExhausted:
            wait = (2 ** attempt) + random.uniform(1, 3)
            st.warning(f"⚠️ Quota hit. Pausing for {wait:.1f}s before retry...")
            time.sleep(wait)
        except Exception as e:
            st.error(f"Generation Error: {e}")
            return None
    st.error("❌ Quota exhausted. Please wait 2 minutes.")
    return None

# --- 3. VIDEO DOWNLOADER (480p Optimized) ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    # 480p ensures the file is small enough to upload fast and save tokens
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV: Unbreakable v12.5")
st.caption("Auto-retry enabled • Full Script + Novel • Vision Only (No Search crashes)")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Episode URL (Disney/YouTube):")
    uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("POV Character:", chars)
    style = st.selectbox("Writing Style:", ["YA Fantasy (Sarah J. Maas)", "Middle Grade (Percy Jackson)", "TV Script Only"])

if st.button("🚀 RUN FULL SYNC", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step A: Get Video
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading video (Quota Optimized)...")
                video_path = download_video(url_input, tmp_dir)

            # Step B: Upload to Gemini Vision
            st.info("☁️ Uploading to Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                st.error("Video processing failed on Google's side.")
                st.stop()

            # Step C: The "Lore-Injected" Prompt
            st.info(f"🧠 Watching & Writing ({style})...")
            
            # We use 1.5 Flash or 2.0 Flash as they are most stable for Vision without tools
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            SYSTEM: You are an expert showrunner for 'Wizards Beyond Waverly Place'.
            
            CHARACTERS (Use for visual identification):
            - Roman: The anxious, responsible brother.
            - Billie: The rebellious wizard with colorful hair.
            - Justin: The dad/teacher.
            - Winter: Roman's best friend.
            - Milo: The younger brother.
            - Giada: The mom.
            
            TASK: Watch the video and generate two outputs.
            
            1. FULL TRANSCRIPT:
            - Extract every line of dialogue.
            - Label speakers correctly based on the visual character guide above.
            
            2. NOVEL CHAPTER:
            - Write a long, immersive chapter from {pov_char}'s POV.
            - Style: {style}.
            - Include internal thoughts (italics) and sensory details.
            
            FORMAT (Strictly follow this separator):
            ---TRANSCRIPT_START---
            [Insert Full Labeled Script Here]
            ---POV_START---
            [Insert Novel Chapter Here]
            """

            response = safe_generate(model, [video_file, prompt])
            
            if response and response.text:
                output = response.text
                if "---POV_START---" in output:
                    parts = output.split("---POV_START---")
                    st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                    st.session_state.novel = parts[1]
                    st.success("✅ Complete!")
                else:
                    st.warning("Could not split output perfectly, showing full text:")
                    st.session_state.transcript = output
                    st.session_state.novel = ""

            # Cleanup
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Critical Error: {e}")

# --- 5. RESULTS TABS ---
if "transcript" in st.session_state:
    tab1, tab2 = st.tabs(["📝 Full Script (Dialogue)", "📖 The Novel (Story)"])
    
    with tab1:
        st.text_area("Copy Script:", st.session_state.transcript, height=600)
        st.download_button("Download Script.txt", st.session_state.transcript, "transcript.txt")
        
    with tab2:
        st.markdown(f"### {pov_char}'s Chapter")
        st.write(st.session_state.novel)
        st.download_button("Download Story.txt", st.session_state.novel, "story.txt")
