import streamlit as st
import google.generativeai as genai
import time
from docx import Document
from io import BytesIO

# 1. MOBILE-FIRST UI CONFIG
st.set_page_config(page_title="Roman Russo Studio", layout="centered") # Centered is better for mobile

# 2. POWERFUL MODEL SETUP
# We use Gemini 2.5 Flash for the 1M token window (perfect for 23min videos)
API_KEY = st.secrets.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Persistence logic
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "chapter" not in st.session_state: st.session_state.chapter = ""

# 3. SEPARATE DOCUMENT CREATOR
def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# 4. SIDEBAR (Fixed for Mobile responsiveness)
with st.sidebar:
    st.header("📝 Production Desk")
    cast_list = st.text_area("Correct Cast Roles:", 
        "Giada: Mother\nTheresa: Grandmother\nJustin: Father\nRoman: Protagonist")
    pov = st.selectbox("Story POV:", ["Roman Russo", "Justin", "Billie"])
    
    st.divider()
    st.info("💡 Tip: Upload your cookies.txt here if recording from a protected site.")

# 5. MAIN APP
st.title("🧙‍♂️ Roman Russo Story")
up_file = st.file_uploader("Upload Video", type=["mp4", "mov"])

if up_file and st.button("🔥 Generate Productions"):
    with st.status("🎬 Processing Episode...") as status:
        # Saving locally for upload
        with open("temp_vid.mp4", "wb") as f:
            f.write(up_file.getbuffer())
        
        # Using Gemini 2.5 Flash
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        video_file = genai.upload_file(path="temp_vid.mp4")
        
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = genai.get_file(video_file.name)

        prompt = f"""
        Role: Professional Scriptwriter and Novelist.
        Cast: {cast_list}
        
        Task 1: Generate a FULL verbatim transcript.
        Task 2: Write a 2500-word chapter from {pov}'s POV.
        
        IMPORTANT: Return the output with the marker '---SPLIT---' between Task 1 and Task 2.
        """
        
        response = model.generate_content([video_file, prompt])
        
        # Splitting into separate storage
        if "---SPLIT---" in response.text:
            parts = response.text.split("---SPLIT---")
            st.session_state.transcript = parts[0]
            st.session_state.chapter = parts[1]
        
        status.update(label="✅ Success!", state="complete")

# 6. SEPARATE DOWNLOAD BUTTONS (Mobile Friendly)
if st.session_state.transcript:
    st.success("Your files are ready for separate download:")
    
    # Using columns to put buttons side-by-side on desktop, stack on mobile
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Download Transcript",
            data=create_docx("Full Episode Transcript", st.session_state.transcript),
            file_name="Episode_Transcript.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with col2:
        st.download_button(
            label="📥 Download Novel Chapter",
            data=create_docx(f"{pov} Chapter", st.session_state.chapter),
            file_name="Novel_Chapter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
