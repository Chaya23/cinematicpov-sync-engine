import streamlit as st
import google.generativeai as genai
import time
import os

# 1. SETUP
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence for results
if "final_output" not in st.session_state:
    st.session_state.final_output = ""

st.title("🧙‍♂️ Roman's Redemption: POV Studio")

# 2. MANUAL POV SELECTOR
pov_choice = st.selectbox(
    "Select Character POV for the Novel:",
    ["Roman Russo", "Justin Russo", "Alex Russo", "Max Russo", "Billie"]
)

up_file = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])

if up_file:
    # Save locally to handle the 10GB limit processing
    with open("episode.mp4", "wb") as f:
        f.write(up_file.getbuffer())

    if st.button(f"🎬 Generate {pov_choice} POV"):
        with st.status("📡 Processing... This can take 2-5 minutes.") as status:
            
            # Step A: Upload to Gemini
            video_file = genai.upload_file(path="episode.mp4")
            
            # Step B: Background monitoring so app doesn't crash
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = genai.get_file(video_file.name)
            
            # Step C: The Comprehensive Prompt
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Identify all speakers in this 'Wizards Beyond Waverly Place' video.
            
            TASK 1: FULL TRANSCRIPT
            Provide a word-for-word transcript. 
            Format: [Character Name]: [Dialogue]
            
            TASK 2: RESEARCH & NOVEL
            Using the events in this video, write a 2,000-word novel chapter.
            The chapter MUST be in the 1st-person POV of {pov_choice}.
            Include internal thoughts and specific details from the episode.
            """
            
            response = model.generate_content([video_file, prompt])
            st.session_state.final_output = response.text
            status.update(label="✅ Production Complete!", state="complete")

# 3. THE RESULT
if st.session_state.final_output:
    st.divider()
    st.markdown(st.session_state.final_output)
