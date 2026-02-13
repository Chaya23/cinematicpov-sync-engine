import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp

# --- 1. SETUP ---
st.set_page_config(page_title="CinematicPOV Vision Sync", layout="wide")

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("Missing GOOGLE_API_KEY in Secrets!")
    st.stop()

# --- 2. VIDEO DOWNLOADER ---
def download_video(url, tmp_dir):
    # Download at lower resolution (480p) to stay under the 2GB Google File limit
    out_path = os.path.join(tmp_dir, "video.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "video.mp4")

# --- 3. MAIN UI ---
st.title("🎬 Vision Sync Engine v11.0")
st.caption("Gemini will now 'Watch' the video for better character matching.")

url_input = st.text_input("Paste Video Link (YouTube/Disney/Solar):")
uploaded_file = st.file_uploader("OR Upload Video File:", type=['mp4', 'mov', 'avi'])

chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
pov_char = st.selectbox("Select POV Character:", chars)

if st.button("🚀 WATCH & SYNC FULL VIDEO", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step 1: Get Video File
            if uploaded_file:
                video_path = os.path.join(tmp_dir, "input_video.mp4")
                with open(video_path, "wb") as f: f.write(uploaded_file.getbuffer())
            else:
                st.info("📥 Downloading video...")
                video_path = download_video(url_input, tmp_dir)

            # Step 2: Upload to Google Files API
            st.info("☁️ Uploading to Gemini Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            
            # Step 3: Wait for Processing
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                st.error("Google failed to process video.")
                st.stop()

            # Step 4: Analyze with Gemini 3 Flash
            st.info("👁️ Gemini is watching and transcribing...")
            model = genai.GenerativeModel('gemini-3-flash') # Using the 2026 flagship
            
            prompt = f"""
            Watch this full video. 
            1. Transcribe the entire episode. 
            2. Match the voices to the characters (Roman, Billie, Justin, etc.).
            3. Use these facts: Roman made the Lacey vase; Billie gets the Staten Island makeover.
            4. Write a 1st-person POV chapter from the perspective of {pov_char}.

            FORMAT:
            ---TRANSCRIPT---
            [Labeled Transcript]
            ---POV---
            [Novel Chapter]
            """

            # The full video is now part of the prompt
            response = model.generate_content([video_file, prompt])
            
            # Display results
            output = response.text
            if "---POV---" in output:
                parts = output.split("---POV---")
                st.session_state.labeled = parts[0].replace("---TRANSCRIPT---", "")
                st.session_state.story = parts[1]
                st.success("✅ Sync Complete!")
            else:
                st.write(output)

            # Cleanup: Delete file from Google storage
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. TABS ---
t1, t2 = st.tabs(["📖 Character Novel", "📝 Labeled Transcript"])
if "story" in st.session_state:
    with t1: st.write(st.session_state.story)
    with t2: st.text_area("Transcript:", st.session_state.labeled, height=500)

        
