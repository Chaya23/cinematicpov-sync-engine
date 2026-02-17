import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
import shutil
from datetime import datetime

# ------------------- CONFIG -------------------
st.set_page_config(page_title="POV DVR Engine", layout="wide", page_icon="📽️")

if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

MODEL_NAME = "gemini-2.0-flash-exp"
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# ------------------- SYSTEM CHECK -------------------
def check_system():
    """Check if yt-dlp and ffmpeg are installed"""
    problems = []
    
    if not shutil.which("yt-dlp"):
        problems.append("❌ yt-dlp not found")
    else:
        try:
            result = subprocess.run(["yt-dlp", "--version"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                problems.append(f"✅ yt-dlp v{result.stdout.strip()}")
        except:
            problems.append("⚠️ yt-dlp error")
    
    if not shutil.which("ffmpeg"):
        problems.append("❌ ffmpeg not found")
    else:
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                problems.append(f"✅ {version}")
        except:
            problems.append("⚠️ ffmpeg error")
    
    return problems

# ------------------- DVR ENGINE -------------------
def run_dvr_with_progress(url, cookies_file=None):
    """Downloads video using yt-dlp"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dvr_rec_{timestamp}.mp4"
    
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", filename,
        url
    ]
    
    if cookies_file:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])
    
    with st.status(f"🎬 Recording: {filename}", expanded=True) as status:
        try:
            st.write("🔍 Analyzing URL...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            log_display = st.empty()
            full_log = []
            
            for line in process.stdout:
                full_log.append(line)
                if any(word in line.lower() for word in ['download', 'merge', 'error']):
                    log_display.code(line.strip())
                
                if "[download] 100%" in line:
                    st.write("🔧 Merging with FFmpeg...")
            
            return_code = process.wait()
            
            if return_code == 0 and os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                status.update(label=f"✅ Saved! ({size_mb:.1f} MB)", state="complete")
                return filename
            else:
                status.update(label="❌ Failed", state="error")
                st.error("**Error Log:**")
                st.code("\n".join(full_log[-10:]))
                return None
                
        except Exception as e:
            status.update(label="❌ Error", state="error")
            st.error(f"Error: {str(e)}")
            return None

# ------------------- UI -------------------
st.title("🎬 POV Cloud DVR Studio")

# System check
with st.sidebar:
    st.subheader("🔧 System Status")
    for item in check_system():
        if "✅" in item:
            st.success(item)
        elif "❌" in item:
            st.error(item)
        else:
            st.warning(item)

# Main tabs
tab_record, tab_library = st.tabs(["🔴 New Recording", "📚 Library"])

with tab_record:
    url = st.text_input(
        "Paste Link (DisneyNow, YouTube, etc.):",
        placeholder="https://disneynow.com/..."
    )
    pov = st.selectbox("Novel POV:", ["Roman", "Billie", "Milo", "Justin", "Winter"])
    cookies = st.file_uploader("🍪 cookies.txt (Upload for Disney/Netflix)", type=["txt"])
    
    if st.button("🚀 Start DVR Process", type="primary"):
        if not url:
            st.error("Please enter a URL!")
        else:
            if not shutil.which("yt-dlp") or not shutil.which("ffmpeg"):
                st.error("❌ Missing dependencies! See sidebar.")
            else:
                saved_file = run_dvr_with_progress(url, cookies)
                if saved_file:
                    st.session_state.recorded_files.append({
                        "file": saved_file,
                        "pov": pov,
                        "url": url[:60],
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.balloons()
                    st.success("✅ Recording saved! Check Library tab to download it!")

with tab_library:
    if not st.session_state.recorded_files:
        st.info("📭 Your library is empty. Start a recording!")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_path = item['file']
            
            with st.container(border=True):
                # File info
                st.write(f"### 🎞️ {os.path.basename(file_path)}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.caption(f"📖 **POV:** {item['pov']}")
                    st.caption(f"⏰ **Time:** {item.get('time', 'Unknown')}")
                
                with col2:
                    if os.path.exists(file_path):
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        st.caption(f"💾 **Size:** {size_mb:.1f} MB")
                        st.caption(f"🔗 **URL:** {item.get('url', 'Unknown')[:30]}...")
                    else:
                        st.error("⚠️ File not found!")
                
                with col3:
                    # Download button for MP4
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label="📥 Download MP4",
                                data=file,
                                file_name=os.path.basename(file_path),
                                mime="video/mp4",
                                key=f"download_{idx}",
                                use_container_width=True
                            )
                
                st.markdown("---")
                
                # AI Processing section
                if os.path.exists(file_path):
                    if st.button("✨ Run AI Production", key=f"ai_{idx}", use_container_width=True):
                        with st.status("AI Processing...") as ai_status:
                            try:
                                # Upload to Gemini
                                st.write("📤 Uploading video to Gemini...")
                                video_file = genai.upload_file(file_path)
                                
                                # Wait for processing
                                st.write("⏳ Waiting for Gemini to process...")
                                while video_file.state.name == "PROCESSING":
                                    time.sleep(2)
                                    video_file = genai.get_file(video_file.name)
                                
                                if video_file.state.name == "FAILED":
                                    st.error("❌ Gemini processing failed")
                                    ai_status.update(label="❌ Failed", state="error")
                                    continue
                                
                                # Generate content
                                st.write("🤖 AI is analyzing the video...")
                                model = genai.GenerativeModel(MODEL_NAME)
                                
                                prompt = f"""Analyze this video from {item['pov']}'s perspective.

Create TWO outputs separated by "---":

1. TRANSCRIPT: Full verbatim transcript with speaker labels
Format: 
SPEAKER_NAME: dialogue text

2. NOVEL CHAPTER: First-person POV narrative from {item['pov']}'s perspective
- Use "I", "me", "my"
- Include internal thoughts and emotions
- Rich sensory details
- Present tense
- Immersive and cinematic

Provide both sections separated by exactly: ---"""
                                
                                resp = model.generate_content([video_file, prompt])
                                
                                # Parse response
                                parts = resp.text.split("---")
                                transcript = parts[0].strip()
                                novel = parts[1].strip() if len(parts) > 1 else "Could not generate novel"
                                
                                ai_status.update(label="✅ Complete!", state="complete")
                                
                                # Display results
                                st.subheader("📜 Transcript")
                                st.text_area(
                                    "Transcript",
                                    transcript,
                                    height=250,
                                    key=f"transcript_{idx}"
                                )
                                
                                st.download_button(
                                    "📥 Download Transcript",
                                    transcript,
                                    file_name=f"transcript_{idx}.txt",
                                    mime="text/plain",
                                    key=f"dl_t_{idx}"
                                )
                                
                                st.subheader(f"📖 {item['pov']}'s Novel")
                                st.text_area(
                                    "Novel Chapter",
                                    novel,
                                    height=350,
                                    key=f"novel_{idx}"
                                )
                                
                                st.download_button(
                                    "📥 Download Novel",
                                    novel,
                                    file_name=f"novel_{item['pov']}_{idx}.txt",
                                    mime="text/plain",
                                    key=f"dl_n_{idx}"
                                )
                                
                            except Exception as e:
                                ai_status.update(label="❌ Error", state="error")
                                st.error(f"AI Error: {str(e)}")

st.markdown("---")
st.caption("🎬 POV Cloud DVR Studio | Powered by yt-dlp + Gemini AI")
