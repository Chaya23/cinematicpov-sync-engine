import streamlit as st
import os, tempfile, time, subprocess
import google.generativeai as genai
from openai import OpenAI
from docx import Document 
from io import BytesIO
import yt_dlp

# --- 1. CONFIG & KEYS ---
st.set_page_config(page_title="Roman's Justice Ultra v19.0", layout="wide", page_icon="🕵️")

# In local terminal, use environment variables or enter manually
API_KEY_GEMINI = st.sidebar.text_input("Gemini API Key:", type="password")
API_KEY_OPENAI = st.sidebar.text_input("OpenAI API Key:", type="password")

if API_KEY_GEMINI and API_KEY_OPENAI:
    genai.configure(api_key=API_KEY_GEMINI)
    client_oa = OpenAI(api_key=API_KEY_OPENAI)

# --- 2. STEALTH DOWNLOADER (Uses your local cookies.txt) ---
def download_stealth(url, cookies_path="cookies.txt"):
    st.info("🛰️ Initiating Stealth Download with Cookie Injection...")
    outtmpl = "episode_raw.mp4"
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best',
        'outtmpl': outtmpl,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'quiet': False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return outtmpl
        except Exception as e:
            st.error(f"Download Error: {e}")
            return None

# --- 3. MAIN APP UI ---
st.title("🧙 Wizards Beyond: Roman's Redemption Engine")
st.markdown("### *Bypassing the Alex-Bias with Script-Syncing*")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("🎞️ Video Input")
    video_url = st.text_input("Paste Hidden Link (VidCloud/Disney/Solar):")
    use_cookies = st.checkbox("Use local cookies.txt for Geobypass?", value=True)
    
with col2:
    st.header("📄 Transcript Sync")
    st.info("Paste the Forever Dreaming / Wiki transcript here for perfect name-matching.")
    raw_transcript_text = st.text_area("Transcript Paste:", height=150, placeholder="[Alex: Hey Justin...]")

# --- 4. THE EXECUTION ---
if st.button("🚀 EXECUTE SYNCED NOVELIZATION", type="primary"):
    if not API_KEY_GEMINI:
        st.error("Missing API Key!")
    else:
        # STEP 1: DOWNLOAD
        video_file = download_stealth(video_url) if video_url else None
        
        if video_file:
            # STEP 2: WHISPER (The Ear)
            st.info("👂 Whisper: Extracting Verbatim Audio...")
            audio_file = "temp_audio.mp3"
            subprocess.run(f"ffmpeg -i {video_file} -ar 16000 -ac 1 -map a {audio_file} -y", shell=True)
            
            with open(audio_file, "rb") as f:
                whisper_data = client_oa.audio.transcriptions.create(model="whisper-1", file=f, response_format="text")
            
            # STEP 3: GEMINI (The Eye)
            st.info("☁️ Gemini: Watching video to match 'Forever Dreaming' names to faces...")
            gen_file = genai.upload_file(path=video_file)
            while gen_file.state.name == "PROCESSING":
                time.sleep(2)
                gen_file = genai.get_file(gen_file.name)

            # STEP 4: THE FUSION PROMPT
            # This is where we tell Gemini to ignore the bias and focus on Roman
            prompt = f"""
            DATA SOURCES:
            1. VERBATIM AUDIO (Whisper): {whisper_data}
            2. OFFICIAL SCRIPT (User Paste): {raw_transcript_text}
            3. VIDEO VISUALS: (Referenced via provided file)

            TASK:
            - Generate a line-by-line script labeling the speaker for every line. 
            - Use the 'Official Script' names to correct any Whisper errors.
            - Write a YA novel chapter from ROMAN'S POV. 
            - Highlight: The moments Justin or Giada praise Billie while ignoring Roman's competence.
            - Theme: Roman's 'Silent Mastery' vs. the 'Legacy Chaos'.
            
            FORMAT:
            ---SCRIPT---
            [Labeled Transcript]
            ---NOVEL---
            [POV Chapter]
            """
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([gen_file, prompt])
            
            # --- 5. RESULTS ---
            if "---NOVEL---" in response.text:
                parts = response.text.split("---NOVEL---")
                final_script = parts[0].replace("---SCRIPT---", "").strip()
                final_novel = parts[1].strip()
                
                st.success("✅ Justice for Roman Processed!")
                
                l, r = st.columns(2)
                with l:
                    st.subheader("📝 Synced Script")
                    st.text_area("Final Line-by-Line", final_script, height=300)
                with r:
                    st.subheader("📖 Roman's POV Chapter")
                    st.text_area("Novelization", final_novel, height=300)

                # Word Doc Creation
                doc = Document()
                doc.add_heading("Roman Russo: The True Family Wizard", 0)
                doc.add_paragraph(final_novel)
                bio = BytesIO()
                doc.save(bio)
                st.download_button("📥 Download Novel Archive", data=bio.getvalue(), file_name="Roman_Justice.docx")

            # Cleanup
            genai.delete_file(gen_file.name)
