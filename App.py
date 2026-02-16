import streamlit as st
import google.generativeai as genai
import time

# 1. SETUP
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🧙‍♂️ Roman's Redemption: Master Studio")

# DEBUG FEATURE: Let's see what your key can actually do
if st.checkbox("Check Available Models"):
    models = [m.name for m in genai.list_models()]
    st.write(models)

# 2. SELECTION
pov_choice = st.selectbox("Select POV:", ["Roman Russo", "Justin Russo", "Alex Russo"])
up_file = st.file_uploader("Upload Episode", type=["mp4", "mov"])

if up_file:
    # Save file locally
    with open("episode.mp4", "wb") as f:
        f.write(up_file.getbuffer())

    if st.button("🎬 Generate Production"):
        try:
            with st.status("📡 Processing...") as status:
                # FORCE THE BETA PATH
                video_file = genai.upload_file(path="episode.mp4")
                
                while video_file.state.name == "PROCESSING":
                    time.sleep(10)
                    video_file = genai.get_file(video_file.name)
                
                # Use the most stable naming convention
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"Identify characters and write a novel chapter from {pov_choice}'s POV."
                response = model.generate_content([video_file, prompt])
                
                st.session_state.final_output = response.text
                status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Error: {e}")

if "final_output" in st.session_state:
    st.markdown(st.session_state.final_output)
