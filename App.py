import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
import re
from datetime import datetime
from docx import Document
from io import BytesIO
import shutil

# ==================== CORE SETUP ====================
st.set_page_config(page_title="POV Studio 2026", layout="wide", page_icon="🎬")

# UPDATED: Using the flagship Gemini 3 Pro model for February 2026
MODEL_ID = "gemini-3-pro-preview" 

# Session State
if "library" not in st.session_state:
    st.session_state.library = []

# API Client
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("⚠️ Add GEMINI_API_KEY to Streamlit secrets!")
    st.stop()

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"❌ Gemini client error: {e}")
    st.stop()

# ==================== HELPER FUNCTIONS ====================
def create_docx(text, title):
    try:
        doc = Document()
        doc.add_heading(title, 0)
        for paragraph in text.split('\n\n'):
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"DOCX error: {e}")
        return None

def check_dependencies():
    missing = []
    if not shutil.which("yt-dlp"): missing.append("yt-dlp")
    if not shutil.which("ffmpeg"): missing.append("ffmpeg")
    return missing

# ==================== PLAYON-STYLE RECORDING ====================
def playon_style_record(url, cookies_file=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dvr_rec_{timestamp}.mp4"
    
    st.write("🔍 Analyzing available videos...")
    list_cmd = ["yt-dlp", "--list-formats", "--no-warnings", url]
    if cookies_file:
        cookies_path = "temp_cookies.txt"
        with open(cookies_path, "wb") as f: f.write(cookies_file.getbuffer())
        list_cmd.extend(["--cookies", cookies_path])
    
    try:
        list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
        if "duration" in list_result.stdout.lower():
            st.text("Available videos found:")
            format_lines = [line for line in list_result.stdout.split('\n') if 'mp4' in line.lower()]
            st.code('\n'.join(format_lines[:5]))
    except: pass

    cmd = [
        "yt-dlp", "--newline", "--no-playlist", "--no-warnings",
        "-f", "(bestvideo[duration>600][ext=mp4]+bestaudio[ext=m4a])/(best[duration>600][ext=mp4])/best",
        "--merge-output-format", "mp4", "--concurrent-fragments", "4",
        "--buffer-size", "16K", "--http-chunk-size", "10M", "-o", filename, url
    ]
    
    if cookies_file:
        cmd.extend(["--cookies", "temp_cookies.txt"])
    
    with st.status(f"🎬 PlayOn-Style Recording: {filename}", expanded=True) as status:
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            log_display = st.empty()
            full_log = []
            for line in process.stdout:
                full_log.append(line)
                if any(word in line.lower() for word in ['download', 'fragment', 'merge']):
                    log_display.code(line.strip())
            
            if process.wait() == 0 and os.path.exists(filename):
                status.update(label="✅ Recorded Successfully", state="complete")
                return filename
            else:
                status.update(label="❌ Recording Failed", state="error")
                return None
        except Exception as e:
            st.error(f"Recording error: {str(e)}")
            return None

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🎬 Studio Setup")
    show_name = st.text_input("Show Title:", "Wizards Beyond Waverly Place", key="show_title")
    cast_input = st.text_area("Edit Cast (Name: Role):", "Roman: Wizard Son\nBillie: Lead Apprentice\nJustin: Dad\nGiada: Mom", height=150, key="cast_list")
    
    names = [n.strip() for n in re.findall(r'^([^:]+):', cast_input, flags=re.MULTILINE)]
    pov_hero = st.selectbox("Select Narrator POV:", options=names if names else ["Default"], key="pov_select")
    
    st.divider()
    st.info("🦊 Upload cookies.txt for Disney+/Netflix")
    c_file = st.file_uploader("Upload cookies.txt", type="txt", key="cookie_up")
    
    with st.expander("🤖 AI Engine (Feb 2026)"):
        st.success(f"Primary: **Gemini 3 Pro**")
        st.caption("Context: 1M Tokens | Output: 64K Tokens")

# ==================== MAIN UI ====================
st.title(f"🎬 {show_name} Production Studio")

tab1, tab2, tab3 = st.tabs(["🎥 PlayOn DVR", "📂 Upload", "🔗 URL Download"])

with tab1:
    dvr_url = st.text_input("Paste Stream URL (Disney+/Netflix):", key="dvr_url")
    if st.button("🔴 START PLAYON DVR", type="primary", use_container_width=True):
        if not dvr_url: st.error("Paste a URL!")
        else:
            saved_file = playon_style_record(dvr_url, c_file)
            if saved_file:
                st.session_state.library.append({"file": saved_file, "show": show_name, "cast": cast_input, "pov": pov_hero, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                st.rerun()

with tab2:
    local_file = st.file_uploader("Select video file:", type=["mp4", "mkv"], key="local_up")
    if st.button("⬆️ Add to Library", use_container_width=True) and local_file:
        fn = f"local_{datetime.now().strftime('%H%M%S')}_{local_file.name}"
        with open(fn, "wb") as f: f.write(local_file.getbuffer())
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

with tab3:
    url = st.text_input("YouTube/Public URL:", key="url_input")
    if st.button("📥 Download", use_container_width=True) and url:
        fn = f"dvr_{datetime.now().strftime('%H%M%S')}.mp4"
        subprocess.run(["yt-dlp", "-f", "mp4", "-o", fn, url])
        if os.path.exists(fn):
            st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
            st.rerun()

# ==================== LIBRARY & AI PROCESSING ====================
st.header("📚 Production Library")
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.markdown(f"### 🎞️ Recording #{idx+1}: `{item['file']}`")
        
        if st.button(f"✨ Run AI Production (Gemini 3 Pro)", key=f"run_{idx}", type="primary"):
            res_area = st.empty()
            full_response = ""
            with st.status("🧠 Gemini 3 Pro is analyzing video...") as status:
                try:
                    file_up = client.files.upload(file=item['file'])
                    while file_up.state == "PROCESSING":
                        time.sleep(3)
                        file_up = client.files.get(name=file_up.name)

                    # GEMINI 3 PRO CONFIG
                    config = types.GenerateContentConfig(
                        max_output_tokens=65000,
                        temperature=0.7,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )

                    prompt = f"Show: {item['show']}. Cast: {item['cast']}. [TRANSCRIPT] Verbatim word-for-word. [NOVEL] 2500+ word immersive novel from {item['pov']} POV."
                    
                    # Trying Gemini 3 Models in order
                    for model in ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro"]:
                        try:
                            response = client.models.generate_content_stream(model=model, contents=[file_up, prompt], config=config)
                            for chunk in response:
                                if chunk.text:
                                    full_response += chunk.text
                                    res_area.write(f"✍️ Generating... ({len(full_response.split())} words)")
                            break
                        except: continue
                    
                    st.session_state[f"res_{idx}"] = full_response
                    status.update(label="✅ Complete!", state="complete")
                    st.rerun()
                except Exception as e: st.error(f"AI Error: {e}")

        if f"res_{idx}" in st.session_state:
            raw = st.session_state[f"res_{idx}"]
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📜 Transcript")
                st.text_area("T", raw.split("[NOVEL]")[0], height=400, key=f"t_{idx}")
                st.download_button("📥 Transcript (.docx)", create_docx(raw, "Transcript"), file_name=f"Transcript_{idx}.docx", key=f"dl_t_{idx}")
            with c2:
                st.subheader(f"📖 {item['pov']}'s POV Novel")
                st.text_area("N", raw.split("[NOVEL]")[-1], height=400, key=f"n_{idx}")
                st.download_button("📥 Novel (.docx)", create_docx(raw, "Novel"), file_name=f"Novel_{idx}.docx", key=f"dl_n_{idx}")
