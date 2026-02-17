import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components
import os
import time
import subprocess
from io import BytesIO
from docx import Document

# ---------------- 1. APP CONFIG & STYLING ----------------
st.set_page_config(page_title="Cinematic POV Engine Pro", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .stDownloadButton button { width: 100%; border-radius: 5px; background-color: #4CAF50; color: white; }
    .stTextArea textarea { font-family: 'Courier New', Courier, monospace; }
    </style>
    """, unsafe_allow_html=True)

# API KEY SETUP
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 Please add GEMINI_API_KEY to your Streamlit Secrets.")

# ---------------- 2. MINI-DVR JAVASCRIPT ----------------
dvr_js = """
<div style="background: #1e1e1e; color: white; padding: 20px; border-radius: 10px; border: 1px solid #333;">
    <h4 style="margin-top:0;">🔴 Mini-DVR Recorder</h4>
    <p style="font-size: 12px; color: #aaa;">Record Disney+/YouTube tabs directly. (Turn off Hardware Acceleration in browser settings to avoid black screen).</p>
    <button id="startBtn" style="background:#ff4b4b; color:white; border:none; padding:10px 15px; border-radius:5px; cursor:pointer;">Start Recording Tab</button>
    <button id="stopBtn" style="background:#333; color:white; border:none; padding:10px 15px; border-radius:5px; cursor:pointer; margin-left:10px;">Stop & Save</button>
    <div id="status" style="margin-top:10px; font-weight:bold; color: #4CAF50;">Status: Ready</div>
</div>

<script>
    let mediaRecorder;
    let recordedChunks = [];
    const statusDiv = document.getElementById('status');

    async function start() {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
            recordedChunks = [];
            
            mediaRecorder.ondataavailable = (e) => { if(e.data.size > 0) recordedChunks.push(e.data); };
            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'dvr_capture.webm';
                a.click();
                statusDiv.innerText = "Status: Video Saved! Upload it below.";
            };

            mediaRecorder.start();
            statusDiv.innerText = "Status: 🔴 RECORDING... (Play your video now)";
        } catch (err) { statusDiv.innerText = "Error: " + err; }
    }

    document.getElementById('startBtn').onclick = start;
    document.getElementById('stopBtn').onclick = () => { if(mediaRecorder) mediaRecorder.stop(); };
</script>
"""

# ---------------- 3. HELPERS ----------------
def create_docx(text):
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ---------------- 4. SIDEBAR (CHARACTER BIBLE) ----------------
with st.sidebar:
    st.title("🎭 Production Desk")
    model_choice = st.selectbox("AI Brain:", ["Gemini 1.5 Pro (Writing)", "Gemini 1.5 Flash (Speed)"])
    pov_actor = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin", "Milo"])
    
    st.divider()
    st.subheader("Visual ID Bible")
    char_cues = st.text_area("Character Cues (Fixes Name Swaps):", 
        "Roman: Small boy, brown hair, anxious, wearing a vest.\n"
        "Billie: Teen girl, streaks in hair, taller than Roman.\n"
        "Justin: Adult male, glasses, glasses/beard, authority figure.", height=150)
    
    st.divider()
    st.subheader("Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt for YouTube/DisneyNow", type=["txt"])

# ---------------- 5. MAIN INTERFACE ----------------
st.title("🎥 Cinematic POV Engine")

tab_record, tab_process = st.tabs(["🔴 1. DVR RECORD", "🧠 2. AI PROCESS"])

with tab_record:
    st.subheader("Step 1: Capture Footage")
    st.info("Open Disney+ or YouTube in a new window, then use the DVR below.")
    components.html(dvr_js, height=220)
    st.link_button("📺 Open Disney+", "https://www.disneyplus.com", use_container_width=True)

with tab_process:
    st.subheader("Step 2: Upload & Generate")
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        vid_file = st.file_uploader("Upload DVR Clip or MP4", type=["webm", "mp4", "mov"])
    with col_in2:
        url_link = st.text_input("OR Paste URL (YT/DisneyNow Only)")

    if st.button("🚀 START PRODUCTION", use_container_width=True):
        if not vid_file and not url_link:
            st.warning("Please provide a video source.")
        else:
            with st.status("🎬 Processing Production...") as status:
                temp_vid = "input_video.mp4"
                
                # Handling URL vs File
                if vid_file:
                    with open(temp_vid, "wb") as f: f.write(vid_file.getbuffer())
                else:
                    status.update(label="⬇️ Downloading URL (yt-dlp)...")
                    cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", temp_vid, url_link]
                    if cookie_file:
                        with open("cookies.txt", "wb") as f: f.write(cookie_file.getbuffer())
                        cmd.extend(["--cookies", "cookies.txt"])
                    subprocess.run(cmd)

                # AI Analysis
                status.update(label="📤 Uploading to Google AI...", state="running")
                gem_file = genai.upload_file(temp_vid)
                while gem_file.state.name == "PROCESSING":
                    time.sleep(2)
                    gem_file = genai.get_file(gem_file.name)

                model_name = "models/gemini-1.5-pro" if "Pro" in model_choice else "models/gemini-1.5-flash"
                model = genai.GenerativeModel(model_name)

                prompt = f"""
                You are a film editor and novelist. Use these cues: {char_cues}.
                
                TASK 1: EXACT TRANSCRIPT
                - Format [Name]: [Dialogue].
                - Identify based on lip movements and heights. 
                - Billie and Roman are different; check hair and height!

                ---SPLIT_HERE---

                TASK 2: FIRST-PERSON NOVEL
                - POV: {pov_actor}. 
                - Convert this scene into a deep Young Adult novel chapter.
                - Focus on {pov_actor}'s internal feelings and observations.
                """

                response = model.generate_content([gem_file, prompt])
                
                if "---SPLIT_HERE---" in response.text:
                    parts = response.text.split("---SPLIT_HERE---")
                    st.session_state.transcript = parts[0].strip()
                    st.session_state.novel = parts[1].strip()
                    st.rerun()

# ---------------- 6. OUTPUT (SEPARATE BOXES) ----------------
if "transcript" in st.session_state:
    st.divider()
    col_res1, col_res2 = st.columns(2)

    with col_res1:
        st.subheader("📜 Transcript (T-Box)")
        st.download_button("📥 Download Transcript (.docx)", create_docx(st.session_state.transcript), f"{pov_actor}_Script.docx", key="dl_t")
        st.text_area("T-Text", st.session_state.transcript, height=500)

    with col_res2:
        st.subheader(f"📖 {pov_actor}'s Chapter (N-Box)")
        st.download_button("📥 Download Novel (.docx)", create_docx(st.session_state.novel), f"{pov_actor}_Novel.docx", key="dl_n")
        st.text_area("N-Text", st.session_state.novel, height=500)
