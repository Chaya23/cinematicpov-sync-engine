import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="CinematicPOV Gemini 3 Sync", layout="wide", page_icon="🎬")

# Ensure API Key is set in Streamlit Secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY. Add it to your Streamlit Cloud Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. VIDEO DOWNLOADER (Optimized for 2026 Vision) ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
        'proxy': st.secrets.get("PROXY_URL"), # Uses proxy if available
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. MAIN INTERFACE ---
st.title("🎬 Vision Sync Engine v11.7")
st.caption("Powered by Gemini 3 Flash-Preview (February 2026 Edition)")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Video Link (DisneyNow / Solar / YouTube):")
    uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select POV Character:", chars)

if st.button("🚀 START AGENTIC VISION SYNC", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step 1: Get Video
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading episode...")
                video_path = download_video(url_input, tmp_dir)

            # Step 2: Upload to Google Files API
            st.info("☁️ Uploading to Gemini 3 Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            
            # Step 3: Wait for Processing
            while video_file.state.name == "PROCESSING":
                st.spinner("🔄 Gemini is analyzing video frames...")
                time.sleep(5)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                st.error("Video processing failed.")
                st.stop()

            # Step 4: Multimodal Analysis
            st.info(f"🧠 {pov_char} is now entering the scene...")
            
            # Using the exact February 2026 Model ID
            model = genai.GenerativeModel('gemini-3-flash-preview')
            
            prompt = f"""
            You are an expert on 'Wizards Beyond Waverly Place'.
            Task: Watch this video and perform 'Agentic Vision' analysis.
            1. Provide a FULL Labeled Transcript (Character: Dialogue).
            2. Grounding: Match Roman with the Lacey vase and Billie with the Staten Island makeover.
            3. Write a deep 1st-person POV novel chapter for {pov_char}.
            
            Format:
            ---TRANSCRIPT---
            [Labeled Transcript]
            ---POV---
            [Story Chapter]
            """

            response = model.generate_content([video_file, prompt])
            
            # Display Results
            output = response.text
            if "---POV---" in output:
                parts = output.split("---POV---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Sync Successful!")
            else:
                st.write(output)

            # Cleanup
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. TABS ---
if "novel" in st.session_state:
    t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])
    with t1:
        st.markdown(f"### {pov_char}'s POV")
        st.write(st.session_state.novel)
        st.download_button("Download Story", st.session_state.novel, "story.txt")
    with t2:
        st.text_area("Full Transcript:", st.session_state.transcript, height=500)
