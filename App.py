import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO

# --- 1. CLOUD INITIALIZATION ---
st.set_page_config(page_title="Roman's Redemption v18.0", layout="wide", page_icon="🪄")

# Check for API Keys in Streamlit Secrets
if "GOOGLE_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("Missing API Keys! Please add them to your Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
client_oa = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. DOCUMENT ARCHIVE BUILDER ---
def create_master_docx(transcript, chapter, pov_name):
    doc = Document()
    doc.add_heading(f'Wizards Beyond: The {pov_name} Chronicles', 0)
    
    doc.add_heading('Official Line-by-Line Speaker Transcript', level=1)
    doc.add_paragraph(transcript)
    
    doc.add_page_break()
    
    doc.add_heading(f'Series Finale Novelization: {pov_name}\'s POV', level=1)
    doc.add_paragraph(chapter)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. SIDEBAR & CHARACTER SETTINGS ---
with st.sidebar:
    st.header("🏆 The Tribunal Panel")
    cast_list = st.text_area("Cast Names:", "Roman, Billie, Justin, Winter, Milo, Giada")
    pov_char = st.selectbox("Focus POV:", [c.strip() for c in cast_list.split(",")])
    st.divider()
    st.info("v18.0: Local Upload Mode (Bypasses Host Blocks)")

# --- 4. MAIN INTERFACE ---
st.title("🪄 Roman's Redemption: Series Ender Engine")
st.markdown("---")
st.subheader("Step 1: Upload the Episode")
uploaded_video = st.file_uploader("Upload Episode (MP4, MKV, or WEBM)", type=['mp4', 'mkv', 'webm'])

if uploaded_video and st.button("🚀 EXECUTE ROMAN'S TRIUMPH", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save uploaded file
        video_path = os.path.join(tmp_dir, uploaded_video.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_video.getbuffer())

        # STEP 1: WHISPER TRANSCRIPTION
        st.info("👂 Whisper: Transcribing every word and stutter...")
        audio_path = os.path.join(tmp_dir, "audio.mp3")
        # Extract audio using ffmpeg
        subprocess.run(f"ffmpeg -i '{video_path}' -ar 16000 -ac 1 -map a '{audio_path}' -y", shell=True, capture_output=True)
        
        with open(audio_path, "rb") as f_a:
            transcript_raw = client_oa.audio.transcriptions.create(
                model="whisper-1", file=f_a, response_format="text"
            )

        # STEP 2: GEMINI VISION ANALYSIS
        st.info("☁️ Gemini: Watching video to match speakers to lines...")
        video_file = genai.upload_file(path=video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        # STEP 3: THE FINAL FUSION
        st.info(f"✍️ Writing the {pov_char} Redemption Arc...")
        
        safety = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # This prompt forces the "Everyone wins" ending you envisioned!
        prompt = f"""
        CAST: {cast_list}
        VERBATIM DIALOGUE: {transcript_raw}
        
        INSTRUCTIONS:
        1. SCRIPT: Create a line-by-line script. Identify which character said each line from the dialogue.
        2. NOVEL: Write a YA novel chapter from {pov_char}'s POV. 
        3. THE THEME: Focus on Roman's growth. Even if the family is chaotic, show his internal mastery.
        4. THE ENDING: Frame this as a series finale where the Tribunal allows everyone to keep their magic, 
           acknowledging Roman as the official 'Family Wizard' for his discipline, while Billie and Milo 
           keep theirs for their bravery/heart.
        
        FORMAT:
        ---SCRIPT---
        [Transcript]
        ---NOVEL---
        [Chapter]
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content([video_file, prompt], safety_settings=safety)
        genai.delete_file(video_file.name)

        if "---NOVEL---" in res.text:
            parts = res.text.split("---NOVEL---")
            st.session_state.final_script = parts[0].replace("---SCRIPT---", "").strip()
            st.session_state.final_novel = parts[1].strip()
            st.success("✅ Archive Generated!")

# --- 5. RESULTS & DOWNLOAD ---
if "final_novel" in st.session_state:
    st.divider()
    l, r = st.columns(2)
    with l:
        st.subheader("📝 Speaker-Sync Transcript")
        st.text_area("Script", st.session_state.final_script, height=400)
    with r:
        st.subheader(f"📖 {pov_char}'s Series Ender")
        st.text_area("Novel", st.session_state.final_novel, height=400)

    st.divider()
    doc_bytes = create_master_docx(st.session_state.final_script, st.session_state.final_novel, pov_char)
    st.download_button(
        label="📥 Download Full Word Archive (.docx)",
        data=doc_bytes,
        file_name=f"Wizard_Redemption_{pov_char}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
           
