import streamlit as st
import google.generativeai as genai
import time
import os

# 1. SETUP & CONFIG
st.set_page_config(page_title="Roman's Redemption Studio", layout="wide")

# Use the exact stable model name to avoid 404
MODEL_ID = "gemini-1.5-flash-002" 

API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence: This stops the 'disappearing result' bug
if "story_result" not in st.session_state:
    st.session_state.story_result = ""

st.title("🧙‍♂️ Roman's Redemption: Master Studio")

# 2. DIRECTOR'S CONSOLE
with st.sidebar:
    st.header("Settings")
    pov_choice = st.selectbox("Select POV:", ["Roman Russo", "Justin Russo", "Alex Russo", "Billie"])
    word_count = st.slider("Target Length:", 500, 3000, 2000)

up_file = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])

if up_file:
    # Save file locally on the server
    temp_path = "current_episode.mp4"
    with open(temp_path, "wb") as f:
        f.write(up_file.getbuffer())

    if st.button(f"🎬 Generate {pov_choice} POV Novel"):
        try:
            with st.status("📡 Processing... Do not close this tab.") as status:
                
                # Step A: Upload to Gemini
                video_file = genai.upload_file(path=temp_path)
                
                # Step B: Indexing Loop
                while video_file.state.name == "PROCESSING":
                    time.sleep(8)
                    video_file = genai.get_file(video_file.name)
                
                # Step C: The "Best Novel" Prompt
                model = genai.GenerativeModel(model_name=MODEL_ID)
                
                mega_prompt = f"""
                Watch this video from 'Wizards Beyond Waverly Place'. 
                
                1. TRANSCRIPT: Create a full dialogue transcript with character names.
                2. NOVEL: Write a {word_count}-word novel chapter. 
                   POV: 1st-person through the eyes of {pov_choice}.
                   TONE: Gritty, cinematic, and deeply internal. 
                   DETAIL: Include specific actions, magic spells used, and background settings seen in the video.
                """
                
                response = model.generate_content([video_file, mega_prompt])
                st.session_state.story_result = response.text
                status.update(label="✅ Production Finished!", state="complete")
                
        except Exception as e:
            st.error(f"Engine Error: {e}")

# 3. THE REVEAL
if st.session_state.story_result:
    st.divider()
    st.markdown(st.session_state.story_result)
    
    # Add a download button for the chapter
    st.download_button("📥 Download Chapter", st.session_state.story_result, file_name="novel_chapter.txt")
