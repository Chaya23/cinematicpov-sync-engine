import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp

# --- 1. SETTINGS ---
st.set_page_config(page_title="CinematicPOV: Masterpiece v12.1", layout="wide", page_icon="✍️")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE VIDEO DOWNLOADER ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. MAIN UI ---
st.title("🎬 CinematicPOV: Masterpiece v12.1")
st.caption("AI Vision + Full Script Extraction + YA Novelization")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Episode Link (Disney/YouTube/Solar):")
    uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select POV Character:", chars)
    style = st.selectbox("Writing Style:", ["YA Fantasy (Sarah J. Maas)", "Snarky Middle Grade", "Gothic Drama"])

# --- 4. THE CORE ENGINE ---
if st.button("🚀 START FULL AUTHORING", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step A: Get Video
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading episode video...")
                video_path = download_video(url_input, tmp_dir)

            # Step B: Upload to Google
            st.info("☁️ Uploading to Gemini 3 Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = genai.get_file(video_file.name)

            # Step C: The Author Prompt
            st.info(f"✍️ Authoring Chapter and Extracting Full Script...")
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=[{'google_search_retrieval': {}}]
            )
            
            prompt = f"""
            SYSTEM INSTRUCTION:
            1. Use Google Search to verify names and plot for 'Wizards Beyond Waverly Place'.
            2. Extract EVERY piece of dialogue from this video.
            
            WRITING TASK:
            Write a LONG, immersive first-person chapter from {pov_char}'s POV. 
            
            STYLE: {style}
            
            FORMAT (DO NOT SKIP EITHER SECTION):
            ---TRANSCRIPT_START---
            [Provide the ENTIRE labeled transcript here. Character Name: Exact Dialogue.]
            ---POV_START---
            [Provide the full-length novel chapter here, including internal thoughts in italics.]
            """

            # Set max_output_tokens high to ensure it doesn't cut off the transcript
            response = model.generate_content(
                [video_file, prompt],
                generation_config={"max_output_tokens": 8192, "temperature": 0.7}
            )
            
            output = response.text
            if "---POV_START---" in output:
                parts = output.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Script and Chapter Finished!")
            else:
                st.write(output)

            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. TABS FOR RESULTS ---
if "novel" in st.session_state:
    # This layout puts them side-by-side or in easy-to-switch tabs
    tab1, tab2 = st.tabs(["📖 The Manuscript (Novel)", "📝 The Full Script (Transcript)"])
    
    with tab1:
        st.subheader(f"Character POV: {pov_char}")
        st.write(st.session_state.novel)
        st.download_button("Download Story", st.session_state.novel, "story.txt")
        
    with tab2:
        st.subheader("Complete Episode Dialogue")
        st.text_area("Transcript Reference:", st.session_state.transcript, height=600)
        st.download_button("Download Script", st.session_state.transcript, "script.txt")
