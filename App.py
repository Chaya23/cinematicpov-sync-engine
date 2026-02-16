import streamlit as st
import google.generativeai as genai
import os

# 1. SETUP - Use the Key you fixed in Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# 2. SESSION ANCHOR - Keeps data alive if site reloads
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "novel_chapter" not in st.session_state:
    st.session_state.novel_chapter = ""

st.title("🧙‍♂️ Roman's Redemption")

# 3. UPLOAD SECTION
up_file = st.file_uploader("Upload 4K Record", type=["mp4", "mov"])

if up_file:
    if st.button("🚀 Start Production"):
        with st.status("🎬 Processing Wizards Footage...") as status:
            # Save the file to server
            with open("temp_video.mp4", "wb") as f:
                f.write(up_file.getbuffer())
            
            # CALL GEMINI AI
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # The prompt for transcription and novelizing
            prompt = """
            1. Transcribe the dialogue from this Wizards Beyond Waverly Place clip.
            2. Write a 2,000-word novel chapter from the 1st-person POV of Roman Russo.
            """
            
            # Note: For real video, you'd use genai.upload_file() here
            response = model.generate_content(prompt)
            
            # Save results to Session State so they don't vanish
            st.session_state.transcript = "TRANSCRIPT: [Dialogue from Wizards Ep 5...]"
            st.session_state.novel_chapter = response.text
            status.update(label="✅ Production Finished!", state="complete")

# 4. RESULTS AREA - Always stays visible
if st.session_state.novel_chapter:
    st.divider()
    with st.expander("📜 View Transcript"):
        st.write(st.session_state.transcript)
    
    st.subheader("📖 Roman Russo's Chapter")
    st.write(st.session_state.novel_chapter)
