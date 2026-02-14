import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import time

# --- 1. MOBILE UI SETUP ---
st.set_page_config(page_title="Roman's Justice Mobile", layout="centered")

st.title("🧙 Roman's Redemption")
st.subheader("Mobile Edition: Video + Transcript Sync")

# --- 2. API KEYS (Sidebar) ---
with st.sidebar:
    st.header("🔑 Credentials")
    GEM_KEY = st.text_input("Gemini API Key:", type="password")
    OA_KEY = st.text_input("OpenAI API Key:", type="password")

if GEM_KEY and OA_KEY:
    genai.configure(api_key=GEM_KEY)
    client_oa = OpenAI(api_key=OA_KEY)

# --- 3. THE UPLOADERS ---
st.info("Step 1: Upload the Episode 3 video from your phone's storage.")
uploaded_video = st.file_uploader("Select Video (.mp4)", type=["mp4", "mov", "avi"])

st.info("Step 2: The Forever Dreaming Transcript is ready to be synced.")
transcript_input = st.text_area("Paste Transcript Here:", height=200)

# --- 4. PROCESSING LOGIC ---
if st.button("🚀 BUILD ROMAN'S NOVEL"):
    if not (GEM_KEY and OA_KEY and uploaded_video):
        st.error("Please provide both keys and the video file!")
    else:
        with st.status("🔮 AI is analyzing Roman's moments...", expanded=True) as status:
            
            # Save temporary file for Gemini
            with open("temp_vid.mp4", "wb") as f:
                f.write(uploaded_video.read())
            
            # Upload to Gemini (Visual Brain)
            st.write("👁️ Gemini is watching the 'Winter & Roman' scenes...")
            video_ai = genai.upload_file(path="temp_vid.mp4")
            while video_ai.state.name == "PROCESSING":
                time.sleep(2)
                video_ai = genai.get_file(video_ai.name)
            
            # Generate the Justice Novel
            st.write("✍️ Writing the 'Series Ender' Perspective...")
            prompt = f"""
            You are Roman Russo's defense attorney and novelist. 
            Use this transcript: {transcript_input}
            And the uploaded video.
            
            1. Match speaker names to faces.
            2. Focus on Episode 3: How Roman is ignored while Billie 'steals' Winter.
            3. Highlight Roman's discipline—he found the wand, he stayed calm during the Phantomus.
            4. Write a YA Novel chapter from Roman's POV.
            5. Add a 'Tribunal Record' at the end proving Roman is the true heir.
            """
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([video_ai, prompt])
            
            status.update(label="✅ Novel Complete!", state="complete")

        # --- 5. RESULTS ---
        st.markdown(response.text)
        
        # Word Doc Export for your phone
        doc = Document()
        doc.add_heading("Wizards Beyond: Roman's Justice", 0)
        doc.add_paragraph(response.text)
        bio = BytesIO()
        doc.save(bio)
        st.download_button("📥 Save Novel to Phone", data=bio.getvalue(), file_name="Roman_Ep3_Novel.docx")

        # Cleanup
        genai.delete_file(video_ai.name)
