import streamlit as st
import google.generativeai as genai
import time

# 1. SETUP
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🧙‍♂️ Roman's Redemption: Master Studio v3.0")

# POV Selector
pov_choice = st.selectbox("Select Character POV:", ["Roman Russo", "Justin Russo", "Alex Russo", "Billie"])
up_file = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])

if up_file:
    # Save file locally on the server
    with open("episode.mp4", "wb") as f:
        f.write(up_file.getbuffer())

    if st.button(f"🎬 Generate {pov_choice} POV"):
        try:
            with st.status("🚀 Powered by Gemini 2.5 Flash...") as status:
                
                # Step A: Upload video
                video_file = genai.upload_file(path="episode.mp4")
                
                # Step B: Wait for the AI to "Watch"
                while video_file.state.name == "PROCESSING":
                    time.sleep(5)
                    video_file = genai.get_file(video_file.name)
                
                # Step C: The High-Thinking Prompt
                # Using Gemini 2.5 Flash for the best balance of speed and logic
                model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                
                prompt = f"""
                Identify all characters in this 'Wizards Beyond Waverly Place' episode.
                1. Provide a full dialogue transcript with names: [Character]: [Line].
                2. Write a 2,000-word novel chapter from the 1st-person POV of {pov_choice}.
                Focus on internal thoughts and the magic used in the scene.
                """
                
                response = model.generate_content([video_file, prompt])
                st.session_state.final_output = response.text
                status.update(label="✅ Success!", state="complete")
                
        except Exception as e:
            st.error(f"Error: {e}")

if "final_output" in st.session_state:
    st.divider()
    st.markdown(st.session_state.final_output)
