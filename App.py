import streamlit as st
import google.generativeai as genai
import time
from docx import Document
from io import BytesIO

# 1. SETUP & THE "FREE TIER" HUB
# Using the model ID that appeared at Index 0 in your list
MODEL_ID = "models/gemini-2.5-flash" 

st.set_page_config(page_title="Roman's Redemption Studio", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence anchors
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# 2. WORD DOCUMENT ENGINE
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    # Cleaning up AI markers like *** or ###
    clean_content = content.replace("**", "").replace("###", "")
    doc.add_paragraph(clean_content)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

st.title("🧙‍♂️ Roman's Redemption: Master Studio v4.0")

# 3. SIDEBAR CONTROLS
with st.sidebar:
    st.header("Studio Controls")
    pov_choice = st.selectbox("Narrator POV:", ["Roman Russo", "Justin Russo", "Alex Russo", "Billie"])
    thought_depth = st.select_slider("Internal Monologue Depth", options=["Standard", "Deep", "Psychological"])
    st.info(f"Connected to: {MODEL_ID} (Free Tier Access)")

up_file = st.file_uploader("Upload Episode (MP4/MOV)", type=["mp4", "mov"])

if up_file:
    # Save video temporarily to the server
    temp_video = "prod_video.mp4"
    with open(temp_video, "wb") as f:
        f.write(up_file.getbuffer())

    if st.button(f"🚀 Begin {pov_choice} Production"):
        try:
            with st.status("🎬 Syncing with Gemini 2.5...") as status:
                model = genai.GenerativeModel(MODEL_ID)
                
                # Step A: Upload to Cloud
                video_file = genai.upload_file(path=temp_video)
                while video_file.state.name == "PROCESSING":
                    time.sleep(5)
                    video_file = genai.get_file(video_file.name)
                
                # Step B: The "Deep Thought" Prompt
                prompt = f"""
                Watch this 'Wizards Beyond Waverly Place' episode carefully.
                
                1. FULL TRANSCRIPT: Character names with time-stamped dialogue.
                2. NOVEL CHAPTER: Write a 2,500-word story in 1st-person POV of {pov_choice}.
                
                WRITING INSTRUCTION ({thought_depth} Mode): 
                Focus heavily on internal thoughts. When a character speaks, describe 
                {pov_choice}'s reaction, their heartbeat, and their secret feelings 
                about magic and family. Make it feel like a professional fantasy novel.
                """
                
                response = model.generate_content([video_file, prompt])
                
                # Saving results
                raw_text = response.text
                if "1." in raw_text and "2." in raw_text:
                    parts = raw_text.split("2.")
                    st.session_state.transcript = parts[0]
                    st.session_state.chapter = parts[1]
                else:
                    st.session_state.transcript = "Transcript generated within the story text."
                    st.session_state.chapter = raw_text
                
                status.update(label="✅ Success!", state="complete")
        except Exception as e:
            st.error(f"Production Error: {e}")

# 4. THE DOWNLOAD HUB
if st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Professional Transcript")
        st.download_button(
            label="💾 Save Transcript as Word",
            data=create_docx("Wizards Transcript", st.session_state.transcript),
            file_name="transcript.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.info("The transcript includes all speaker names and timing.")
        
    with col2:
        st.subheader(f"📖 {pov_choice}'s Chapter")
        st.download_button(
            label="💾 Save Chapter as Word",
            data=create_docx(f"The Story of {pov_choice}", st.session_state.chapter),
            file_name="novel_chapter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.info("The novel includes the deep internal thoughts you requested.")
