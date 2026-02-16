import streamlit as st
import google.generativeai as genai
import time
import os

# 1. SETUP
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🧙‍♂️ Roman's Redemption: POV Studio")

pov_choice = st.selectbox("Select Character POV:", ["Roman Russo", "Justin Russo", "Alex Russo"])
up_file = st.file_uploader("Upload Episode", type=["mp4", "mov"])

if up_file:
    # Save file to server
    with open("episode.mp4", "wb") as f:
        f.write(up_file.getbuffer())

    if st.button(f"🎬 Generate {pov_choice} POV"):
        try:
            with st.status("📡 Syncing with Gemini...") as status:
                # Step A: Upload
                video_file = genai.upload_file(path="episode.mp4")
                st.write(f"File uploaded: {video_file.name}")
                
                # Step B: Wait loop with safety check
                while video_file.state.name == "PROCESSING":
                    time.sleep(10) # Wait 10 seconds between checks
                    video_file = genai.get_file(video_file.name)
                
                if video_file.state.name == "FAILED":
                    st.error("Gemini failed to process the video. Try a smaller file.")
                    st.stop()

                # Step C: The Request
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Transcribe this video and write a novel chapter from {pov_choice}'s POV."
                
                # We wrap this in a final check to prevent 'NotFound' errors
                response = model.generate_content([video_file, prompt])
                st.session_state.final_output = response.text
                status.update(label="✅ Success!", state="complete")
                
        except Exception as e:
            st.error(f"System Error: {e}. Please try refreshing the app.")
