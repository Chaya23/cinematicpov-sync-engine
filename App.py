import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
import shutil
import tempfile
from datetime import datetime

# ------------------- 1. CONFIG & MODEL -------------------
st.set_page_config(page_title="CastScript Pro 2026", layout="wide", page_icon="🎬")

# SESSION STATE
if "dvr_library" not in st.session_state:
    st.session_state.dvr_library = []

# Using the newest Gemini 3 Flash (GA Dec 2025)
MODEL_NAME = "gemini-3-flash" 
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- 2. DVR ENGINE (MOBILE OPTIMIZED) -------------------
def download_dvr(url, cookies_file=None):
    """Downloads using -t mp4 which ensures H.264/AAC for mobile phones."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"dvr_{timestamp}.mp4"
    
    # -S vcodec:h264,acodec:aac is the secret to fixing phone playback crashes
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "-S", "vcodec:h264,acodec:aac", 
        "--merge-output-format", "mp4",
        "-o", filename,
        url
    ]
    
    if cookies_file:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])
    
    with st.status(f"📥 DVR Recording: {filename}", expanded=True) as status:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        log_box = st.empty()
        for line in process.stdout:
            if "%" in line:
                log_box.caption(f"Progress: {line.strip()}")
        
        process.wait()
        if process.returncode == 0:
            status.update(label="✅ Ready for Production", state="complete")
            return filename
        return None

# ------------------- 3. UI LAYOUT -------------------
st.title("🎬 POV Cloud DVR & Production")
st.caption("2026 Edition | Unrestricted Mode | Gemini 3 Flash")

tab1, tab2 = st.tabs(["🔴 New Recording", "📚 Production Library"])

with tab1:
    url_input = st.text_input("Paste Video Link:")
    pov_character = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin", "Milo"])
    cookie_file = st.file_uploader("🍪 Upload cookies.txt (For Disney/YouTube)", type=["txt"])
    
    if st.button("🚀 Start DVR Process", use_container_width=True):
        if url_input:
            saved_file = download_dvr(url_input, cookie_file)
            if saved_file:
                st.session_state.dvr_library.append({"file": saved_file, "pov": pov_character})
                st.toast("Recording Finished!", icon="✅")
        else:
            st.error("Missing URL!")

with tab2:
    if not st.session_state.dvr_library:
        st.info("Queue a recording to start.")
    else:
        for idx, item in enumerate(st.session_state.dvr_library):
            with st.container(border=True):
                col_name, col_dl, col_ai = st.columns([2, 1, 1])
                file_path = item['file']
                
                col_name.write(f"🎥 **{file_path}**")
                
                # PHONE-SAFE DOWNLOAD
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        col_dl.download_button("📥 Save to Phone", f, file_name=file_path, mime="video/mp4", key=f"dl_{idx}")
                
                if col_ai.button("✨ Write Novel", key=f"btn_{idx}"):
                    with st.status("🧠 Gemini 3 Flash is Analyzing...") as status:
                        # Upload to Google
                        gen_file = genai.upload_file(file_path)
                        while gen_file.state.name == "PROCESSING":
                            time.sleep(2)
                            gen_file = genai.get_file(gen_file.name)
                        
                        # Process
                        model = genai.GenerativeModel(MODEL_NAME)
                        prompt = f"""
                        TASK:
                        1. Write a full transcript with speaker names.
                        2. Write a novel chapter in the first-person POV of {item['pov']}.
                        Split sections with '===SPLIT==='
                        """
                        response = model.generate_content([gen_file, prompt])
                        st.session_state[f"res_{idx}"] = response.text.split("===SPLIT===")
                        status.update(label="✅ Production Complete!", state="complete")

                # THE T-BOX AND N-BOX (Side-by-Side)
                if f"res_{idx}" in st.session_state:
                    st.divider()
                    t_box, n_box = st.columns(2)
                    results = st.session_state[f"res_{idx}"]
                    
                    with t_box:
                        st.subheader("📜 Transcript (T-Box)")
                        st.text_area("Transcript Text", results[0], height=400, key=f"ta_{idx}")
                    
                    with n_box:
                        st.subheader(f"📖 {item['pov']}'s Novel (N-Box)")
                        st.text_area("Novel Text", results[1] if len(results) > 1 else "", height=400, key=f"na_{idx}")
