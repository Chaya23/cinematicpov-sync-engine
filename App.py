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
                # USE THE UNIVERSAL NAME TO PREVENT 404
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Step A: Upload
                video_file = genai.upload_file(path="episode.mp4")
                
                # Step B: Indexing Loop (Crucial for large files)
                while video_file.state.name == "PROCESSING":
                    time.sleep(10)
                    video_file = genai.get_file(video_file.name)
                
                if video_file.state.name == "FAILED":
                    st.error("Video processing failed on Google's side.")
                    st.stop()

                # Step C: Generate Novel & Transcript
                prompt = f"""
                Research 'Wizards Beyond Waverly Place'. 
                1. Provide a full dialogue transcript with character names. 
                2. Write a long novel chapter in 1st-person POV of {pov_choice}.
                """
                
                # If v1beta is causing errors, the library handles the fallback here
                response = model.generate_content([video_file, prompt])
                
                # Save to session so it doesn't vanish if you switch apps
                st.session_state.final_output = response.text
                status.update(label="✅ Success!", state="complete")
                
        except Exception as e:
            # If it STILL 404s, it means the API key is not active for 1.5 yet
            st.error(f"Engine Error: {e}")
            st.info("Try checking your Google AI Studio dashboard to ensure the API key is active.")

if "final_output" in st.session_state:
    st.divider()
    st.write(st.session_state.final_output)
