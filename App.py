import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="CinematicPOV Vision Sync", layout="wide", page_icon="🎬")

# Ensure API Key is present
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Please add GOOGLE_API_KEY to your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE VIDEO DOWNLOADER (Optimized for Vision) ---
def download_video_for_vision(url, tmp_dir):
    # We download in 480p/720p to keep upload speeds fast and stay under file limits
    out_path = os.path.join(tmp_dir, "episode_video.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
        'proxy': st.secrets.get("PROXY_URL"), # Optional proxy fix from earlier
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode_video.mp4")

# --- 3. MAIN UI ---
st.title("🎬 CinematicPOV Vision Sync v11.5")
st.info("Gemini 3 Flash will now WATCH the video to identify characters perfectly.")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Paste Video Link (Disney/Solar/YouTube):")
    uploaded_video = st.file_uploader("OR Upload Video File (Max 200MB):", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("POV Character:", chars + ["Custom..."])
    if pov_char == "Custom...":
        pov_char = st.text_input("Enter Name:")

# --- 4. THE SYNC LOGIC ---
if st.button("🚀 START VISION SYNC", type="primary"):
    if not url_input and not uploaded_video:
        st.warning("Please provide a video source!")
        st.stop()

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step 1: Get the Video
            if uploaded_video:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f:
                    f.write(uploaded_video.getbuffer())
            else:
                st.info("📥 Downloading episode video...")
                video_path = download_video_for_vision(url_input, tmp_dir)

            # Step 2: Upload to Google's Vision Engine
            st.info("☁️ Uploading to Gemini Files API...")
            video_file = genai.upload_file(path=video_path)
            
            # Step 3: Wait for Google to "Process" the video
            progress_bar = st.progress(0)
            status_text = st.empty()
            while video_file.state.name == "PROCESSING":
                status_text.text("🔄 Gemini is 'watching' and processing frames...")
                time.sleep(5)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                st.error("Google Vision processing failed. Try a different video.")
                st.stop()

            # Step 4: AI Analysis with Fallback Logic
            st.info("🧠 Analyzing Characters & Plot...")
            
            # Try 2026 models in order of intelligence
            models_to_try = ['gemini-3-flash-preview', 'gemini-3-flash', 'gemini-2.5-flash']
            
            prompt = f"""
            Task: Watch this video carefully.
            1. Create a full transcript with Character Names labeled.
            2. Grounding Facts: Roman made the Lacey vase; Billie gets the Staten Island makeover.
            3. Write a 1st-person POV chapter for {pov_char} based on the episode events.
            
            Format your response as:
            ---TRANSCRIPT_START---
            [Labeled Transcript]
            ---POV_START---
            [Story Chapter]
            """

            response = None
            for m_name in models_to_try:
                try:
                    model = genai.GenerativeModel(m_name)
                    response = model.generate_content([video_file, prompt])
                    st.caption(f"Success using model: {m_name}")
                    break
                except Exception as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        continue # Try the next model in the list
                    else:
                        raise e

            if not response:
                st.error("No compatible Gemini models found for your API key.")
                st.stop()

            # Step 5: Parse & Display
            output = response.text
            if "---POV_START---" in output:
                parts = output.split("---POV_START---")
                st.session_state.labeled_transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.pov_story = parts[1]
                st.success("✅ Sync Complete!")
            else:
                st.write(output)

            # CLEANUP: Delete file from Google storage to save space
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Error: {e}")

# --- 5. RESULTS DISPLAY ---
if "pov_story" in st.session_state:
    tab1, tab2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])
    with tab1:
        st.markdown(f"### {pov_char}'s POV")
        st.write(st.session_state.pov_story)
        st.download_button("Download Story", st.session_state.pov_story, "chapter.txt")
    with tab2:
        st.text_area("Full Transcript:", st.session_state.labeled_transcript, height=400)
