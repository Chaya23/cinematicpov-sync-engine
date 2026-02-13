import streamlit as st
import os, tempfile, time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import yt_dlp

# --- 1. CONFIG ---
st.set_page_config(page_title="CinematicPOV: Unblocked Studio", layout="wide", page_icon="✍️")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. SAFETY SETTINGS (The Fix for 'OTHER' Block) ---
# This disables the strict filters that often block TV episode analysis
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- 3. UI ---
st.title("🎬 CinematicPOV Studio v13.3")
st.caption("Safety Bypass Enabled • Side-by-Side Verification")

with st.expander("📺 Video & Style", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        url_input = st.text_input("Episode URL:")
        uploaded = st.file_uploader("Upload Video:", type=['mp4'])
    with col2:
        pov_char = st.selectbox("POV Character:", ["Roman", "Billie", "Justin", "Winter", "Milo"])
        style = st.selectbox("Style:", ["YA Novel", "Middle Grade"])

if st.button("🚀 SYNC & AUTHOR", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Download
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': os.path.join(tmp_dir, "ep.mp4"), 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url_input])
                video_path = os.path.join(tmp_dir, "ep.mp4")

            # Upload
            st.info("☁️ Uploading...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            # --- THE UNBLOCKED CALL ---
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Observe the character dynamics in this video file. 
            
            1. DIALOGUE LOG: Summarize the key spoken interactions between characters like Roman, Billie, and Justin.
            2. CREATIVE STORY: Write a first-person narrative chapter for {pov_char} in {style} style.
            
            Focus on the emotional themes of the episode (the leopard print makeover, the broken Lacey vase).
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Dialogue Log]
            ---POV_START---
            [Novel Chapter]
            """

            # Applying Safety Settings here
            response = model.generate_content(
                [video_file, prompt],
                safety_settings=safety_settings,
                generation_config={"max_output_tokens": 8192}
            )
            
            # Check if blocked again
            if not response.candidates:
                st.error(f"Blocked by Google Filters. Reason: {response.prompt_feedback}")
            else:
                parts = response.text.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Studio View Ready!")

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Error: {e}")

# --- DISPLAY ---
if "transcript" in st.session_state:
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Dialogue Log")
        st.text_area("Script", st.session_state.transcript, height=800)
    with r:
        st.subheader(f"📖 {pov_char}'s POV")
        st.text_area("Story", st.session_state.novel, height=800)
