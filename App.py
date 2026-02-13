import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Masterpiece 12.4", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. QUOTA-SAFE RETRY WRAPPER ---
def safe_generate(model, content, max_retries=5):
    for attempt in range(max_retries):
        try:
            # Added generation_config to optimize for longer narrative output
            return model.generate_content(
                content, 
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 8192
                }
            )
        except exceptions.ResourceExhausted:
            wait = (2 ** attempt) + random.uniform(0, 1)
            st.warning(f"⚠️ Quota hit. Retrying in {wait:.1f}s...")
            time.sleep(wait)
        except Exception as e:
            raise e
    raise Exception("❌ Quota exhausted.")

# --- 3. UI ---
st.title("🎬 CinematicPOV: Author Edition v12.4")
st.caption("Fixed: google_search tool update for Gemini 3/2.5.")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Episode URL:")
    uploaded = st.file_uploader("OR Upload Video:", type=['mp4'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("POV Character:", chars)
    style = st.selectbox("Writing Style:", ["YA Novel (S.J. Maas)", "Middle Grade (Riordan)"])

if st.button("🚀 AUTHOR FULL CHAPTER", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Video Handling
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': os.path.join(tmp_dir, "ep.mp4"), 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url_input])
                video_path = os.path.join(tmp_dir, "ep.mp4")

            # Upload
            st.info("☁️ Uploading to Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = genai.get_file(video_file.name)

            # Analysis with CORRECT Tool Name
            st.info(f"✍️ Authoring full chapter...")
            
            # THE FIX: Use 'google_search' instead of 'google_search_retrieval'
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                tools=[{'google_search': {}}] 
            )
            
            prompt = f"""
            Identify characters and extract dialogue from this video.
            
            CONTEXT: Wizards Beyond Waverly Place, Season 2 Episode 2.
            STORY: Write a LONG first-person chapter from {pov_char}'s POV. 
            Include: The leopard print makeover, the 'Lacey' vase, and the Changeling monster.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Full Labeled Script]
            ---POV_START---
            [Novel Chapter]
            """

            response = safe_generate(model, [video_file, prompt])
            output = response.text
            
            if "---POV_START---" in output:
                parts = output.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Success!")
            else:
                st.write(output)

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- DISPLAY ---
if "novel" in st.session_state:
    t1, t2 = st.tabs(["📖 The Manuscript", "📝 Full Transcript"])
    with t1:
        st.write(st.session_state.novel)
    with t2:
        st.text_area("Dialogue:", st.session_state.transcript, height=500)
