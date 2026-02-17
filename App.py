import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(page_title="POV DVR Pro", layout="wide")

# Using the newest Gemini 3 Flash (optimized for mobile/fast video)
MODEL_NAME = "gemini-3-flash" 

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. CAST SELECTOR & POV ---
st.sidebar.header("🎭 Studio Cast & POV")
pov_hero = st.sidebar.selectbox("Main POV Character:", ["Roman", "Billie", "Milo", "Justin", "Winter"])

st.sidebar.subheader("Characters in this Episode")
# This allows you to define who is who so the AI doesn't guess
cast_info = st.sidebar.text_area(
    "Identify Cast (Name: Description)", 
    "Roman: Young wizard, sarcastic.\nBillie: Mysterious new student.\nJustin: The mentor figure.",
    height=150
)

# --- 3. THE DVR (NETFLIX/DISNEY READY) ---
def dvr_download(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"episode_{ts}.mp4"
    
    # -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4' is the secret for phone-playability
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    
    if cookies:
        with open("cookies.txt", "wb") as f: f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])

    with st.status("🎬 Recording from Stream..."):
        # We use a subprocess to capture the video stream like a cloud DVR
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0: return fn
        st.error(f"DVR Error: {p.stderr}")
        return None

# --- 4. MAIN UI ---
st.title("🎬 POV Cloud DVR & Production Studio")

u_input = st.text_input("Paste Link (Disney+, Netflix, etc.):")
c_file = st.file_uploader("Upload cookies.txt for Paid Streams", type="txt")

if st.button("🚀 Record & Start Production"):
    video_path = dvr_download(u_input, c_file)
    if video_path:
        st.session_state.library.append({"file": video_path, "pov": pov_hero})

# --- 5. PRODUCTION LIBRARY ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **Episode Recorded:** {item['file']}")
        
        if st.button(f"✨ Run Full AI Analysis", key=f"ai_{idx}"):
            with st.status("🧠 AI is processing 24 minutes of video..."):
                # 1. Upload to Gemini Cloud
                gf = genai.upload_file(item['file'])
                while gf.state.name == "PROCESSING":
                    time.sleep(3)
                    gf = genai.get_file(gf.name)
                
                # 2. THE PROMPT (Designed to prevent cutoff)
                # We ask for the transcript in a way that prioritizes dialogue density
                model = genai.GenerativeModel(MODEL_NAME)
                full_prompt = f"""
                CAST REFERENCE: {cast_info}
                
                TASK:
                Watch this full 24-minute video.
                1. Provide a VERBATIM TRANSCRIPT with speaker labels. 
                Use the Cast Reference to identify characters.
                
                2. After the transcript, write a first-person Novel Chapter 
                from {item['pov']}'s perspective.
                
                Format: 
                [TRANSCRIPT]
                ...Dialogue...
                [END TRANSCRIPT]
                [NOVEL]
                ...Narrative...
                """
                
                response = model.generate_content([gf, full_prompt])
                st.session_state[f"prod_{idx}"] = response.text

        # SEPARATE BOXES
        if f"prod_{idx}" in st.session_state:
            res_text = st.session_state[f"prod_{idx}"]
            
            # Split the Transcript and Novel for separate boxes
            parts = res_text.split("[END TRANSCRIPT]")
            transcript_box = parts[0].replace("[TRANSCRIPT]", "").strip()
            novel_box = parts[1].replace("[NOVEL]", "").strip() if len(parts) > 1 else ""

            t_col, n_col = st.columns(2)
            with t_col:
                st.subheader("📜 T-Box (Full Transcript)")
                st.text_area("Transcript", transcript_box, height=500, key=f"t_area_{idx}")
            with n_col:
                st.subheader(f"📖 N-Box ({item['pov']}'s Novel)")
                st.text_area("Novel", novel_box, height=500, key=f"n_area_{idx}")

            # DOWNLOAD TO PHONE (CRASH-PROOF)
            with open(item['file'], "rb") as f:
                st.download_button("📥 Save MP4 to Phone", f, file_name=item['file'], mime="video/mp4")
