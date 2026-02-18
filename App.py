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

# UPDATED: Use the latest Gemini 2.0 models (Standard & Thinking)
# Priority: Flash 2.0 (Fast/Stable) > Thinking (Creative) > Pro 1.5 (Fallback)
MODEL_ID = "gemini-2.0-flash" 

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
    """Create DOCX file"""
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
    """Check if yt-dlp and ffmpeg exist"""
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    return missing

# ==================== PLAYON-STYLE RECORDING ====================
def playon_style_record(url, cookies_file=None):
    """
    PlayOn-style recording: Downloads stream directly (NOT screen capture)
    Works with Disney+, Netflix, etc. when cookies provided
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dvr_rec_{timestamp}.mp4"
    
    # First, list all available formats to find the longest video (full episode, not trailer)
    st.write("🔍 Analyzing available videos...")
    
    list_cmd = ["yt-dlp", "--list-formats", "--no-warnings", url]
    if cookies_file:
        cookies_path = "temp_cookies.txt"
        with open(cookies_path, "wb") as f:
            f.write(cookies_file.getbuffer())
        list_cmd.extend(["--cookies", cookies_path])
    
    try:
        # Get format list
        list_result = subprocess.run(
            list_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Show what was found
        if "duration" in list_result.stdout.lower():
            st.text("Available videos found:")
            format_lines = [line for line in list_result.stdout.split('\n') 
                          if 'mp4' in line.lower() or 'duration' in line.lower()]
            st.code('\n'.join(format_lines[:10]))  # Show first 10 formats
    except:
        pass  # Continue even if listing fails
    
    # PlayOn-style download command with duration filter
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "--no-warnings",
        # CRITICAL: Only download videos longer than 10 minutes (filters out trailers)
        "-f", "(bestvideo[duration>600][ext=mp4]+bestaudio[ext=m4a])/(best[duration>600][ext=mp4])/(bestvideo[ext=mp4]+bestaudio[ext=m4a])/best",
        "--merge-output-format", "mp4",
        # Speed optimizations (like PlayOn)
        "--concurrent-fragments", "4",  # Download 4 chunks at once
        "--buffer-size", "16K",
        "--http-chunk-size", "10M",
        # Output
        "-o", filename,
        url
    ]
    
    # Add cookies if provided
    if cookies_file:
        cookies_path = "temp_cookies.txt"
        with open(cookies_path, "wb") as f:
            f.write(cookies_file.getbuffer())
        cmd.extend(["--cookies", cookies_path])
    
    # Execute with live progress
    with st.status(f"🎬 PlayOn-Style Recording: {filename}", expanded=True) as status:
        try:
            st.write("📡 Connecting to stream...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            log_display = st.empty()
            full_log = []
            speed = "N/A"
            
            for line in process.stdout:
                full_log.append(line)
                
                # Extract speed
                if "iB/s" in line:
                    speed_match = re.search(r'at\s+([\d.]+\s*[KMG]iB/s)', line)
                    if speed_match:
                        speed = speed_match.group(1)
                
                # Show progress
                if any(word in line.lower() for word in ['download', 'fragment', 'merge']):
                    log_display.code(line.strip())
                
                if "[download] 100%" in line:
                    st.write("🔧 Merging video + audio (FFmpeg)...")
            
            return_code = process.wait()
            
            if return_code == 0 and os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                status.update(
                    label=f"✅ Recorded! {size_mb:.1f} MB @ {speed}",
                    state="complete"
                )
                return filename
            else:
                status.update(label="❌ Recording Failed", state="error")
                st.error("**Error Log:**")
                st.code("\n".join(full_log[-15:]))
                
                # Show helpful hints
                if "ERROR: unable" in "\n".join(full_log).lower():
                    st.warning("💡 This site needs cookies! Upload cookies.txt in sidebar.")
                elif "403" in "\n".join(full_log):
                    st.warning("💡 Access forbidden. Upload fresh cookies from your browser.")
                
                return None
                
        except Exception as e:
            status.update(label="❌ Error", state="error")
            st.error(f"Recording error: {str(e)}")
            return None

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🎬 Studio Setup")
    
    show_name = st.text_input(
        "Show Title:",
        "Wizards Beyond Waverly Place",
        key="show_title"
    )
    
    cast_input = st.text_area(
        "Edit Cast (Name: Role):",
        "Roman: Wizard Son\nBillie: Lead Apprentice\nJustin: Dad\nGiada: Mom\nWinter: Friend\nMilo: Friend",
        height=150,
        key="cast_list",
        help="Format: Name: Role (one per line)"
    )
    
    # Dynamic POV selector
    names = [n.strip() for n in re.findall(r'^([^:]+):', cast_input, flags=re.MULTILINE)]
    if not names:
        names = ["Default"]
    
    pov_hero = st.selectbox(
        "Select Narrator POV:",
        options=names,
        key="pov_select",
        help="Which character's perspective for the novel"
    )
    
    st.divider()
    st.info("🦊 Upload cookies.txt for Disney+/Netflix")
    c_file = st.file_uploader(
        "Upload cookies.txt",
        type="txt",
        key="cookie_up",
        help="Export from Firefox/Chrome while logged into Disney+"
    )
    
    st.divider()
    
    # System status
    with st.expander("🔧 System Check"):
        missing = check_dependencies()
        if missing:
            st.error(f"⚠️ Missing: {', '.join(missing)}")
            st.caption("Add 'yt-dlp' to requirements.txt")
            st.caption("Add 'ffmpeg' to packages.txt")
        else:
            st.success("✅ Ready to record!")
    
    # AI Model status
    with st.expander("🤖 AI Model Check"):
        if client:
            st.caption("Will try these Gemini models in order:")
            st.code("""1. gemini-2.0-flash
2. gemini-2.0-flash-thinking-exp
3. gemini-1.5-pro""")
            st.success("✅ API key configured")
        else:
            st.error("❌ No Gemini API client")

# ==================== MAIN UI ====================
st.title(f"🎬 {show_name} Production Studio")
st.caption("PlayOn-Style Recording + Gemini 2.0 AI Pipeline")

# Recording tabs
tab1, tab2, tab3 = st.tabs([
    "🎥 PlayOn DVR (Disney+/Netflix)",
    "📂 Upload Video",
    "🔗 URL Download (YouTube)"
])

# TAB 1: PLAYON-STYLE DVR
with tab1:
    st.subheader("🎥 PlayOn-Style Stream Recording")
    
    st.markdown("""
    **How it works:**
    - Downloads stream directly (NOT screen capture)
    - No blank screens - works with DRM content
    - Fast downloads (4x parallel connections)
    - Requires cookies.txt for Disney+/Netflix
    """)
    
    dvr_url = st.text_input(
        "Paste Disney+/Netflix/Hulu URL:",
        placeholder="https://www.disneyplus.com/video/...",
        key="dvr_url"
    )
    
    if st.button("🔴 START PLAYON DVR", type="primary", use_container_width=True):
        if not dvr_url:
            st.error("⚠️ Paste a URL first!")
        elif not c_file and ("disney" in dvr_url.lower() or "netflix" in dvr_url.lower()):
            st.error("⚠️ Disney+/Netflix require cookies! Upload cookies.txt in sidebar.")
        else:
            missing = check_dependencies()
            if missing:
                st.error(f"❌ Cannot record: {', '.join(missing)} not installed")
                st.info("Add yt-dlp to requirements.txt and ffmpeg to packages.txt")
            else:
                saved_file = playon_style_record(dvr_url, c_file)
                
                if saved_file:
                    st.session_state.library.append({
                        "file": saved_file,
                        "show": show_name,
                        "cast": cast_input,
                        "pov": pov_hero,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "url": dvr_url[:80]
                    })
                    st.balloons()
                    st.success("✅ Recorded! See library below to process with AI.")
                    st.rerun()

# TAB 2: UPLOAD
with tab2:
    st.subheader("📂 Upload Existing Video")
    
    local_file = st.file_uploader(
        "Select video file:",
        type=["mp4", "mkv", "mov", "avi", "webm"],
        key="local_up"
    )
    
    if st.button("⬆️ Add to Library", use_container_width=True):
        if not local_file:
            st.error("⚠️ Select a file first!")
        else:
            fn = f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{local_file.name}"
            with st.spinner("Uploading..."):
                with open(fn, "wb") as f:
                    f.write(local_file.getbuffer())
            
            st.session_state.library.append({
                "file": fn,
                "show": show_name,
                "cast": cast_input,
                "pov": pov_hero,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "url": "Local Upload"
            })
            st.success("✅ Added to library!")
            st.rerun()

# TAB 3: URL DOWNLOAD
with tab3:
    st.subheader("🔗 Direct URL Download")
    st.caption("For YouTube and public sites (no cookies needed)")
    
    url = st.text_input(
        "Video URL:",
        placeholder="https://youtube.com/watch?v=...",
        key="url_input"
    )
    
    if st.button("📥 Download", use_container_width=True):
        if not url:
            st.error("⚠️ Enter a URL first!")
        else:
            fn = f"dvr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", fn,
                url
            ]
            
            with st.status("📥 Downloading..."):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    if result.returncode == 0 and os.path.exists(fn):
                        st.session_state.library.append({
                            "file": fn,
                            "show": show_name,
                            "cast": cast_input,
                            "pov": pov_hero,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "url": url[:80]
                        })
                        st.success("✅ Downloaded!")
                        st.rerun()
                    else:
                        st.error(f"Download failed:\n{result.stderr[-500:]}")
                except subprocess.TimeoutExpired:
                    st.error("❌ Download timeout (10 min limit)")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==================== LIBRARY & AI PROCESSING ====================
st.markdown("---")
st.header("📚 Production Library")

if not st.session_state.library:
    st.info("📭 Library empty. Record or upload a video above!")
else:
    for idx, item in enumerate(st.session_state.library):
        with st.container(border=True):
            # File info
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### 🎞️ Recording #{idx + 1}")
                st.caption(f"**File:** `{item['file']}`")
                st.caption(f"**Show:** {item['show']}")
            
            with col2:
                st.caption(f"**POV:** {item['pov']}")
                st.caption(f"**Time:** {item.get('timestamp', 'Unknown')}")
                if os.path.exists(item['file']):
                    size_mb = os.path.getsize(item['file']) / (1024 * 1024)
                    st.caption(f"**Size:** {size_mb:.1f} MB")
            
            with col3:
                # Download MP4
                if os.path.exists(item['file']):
                    with open(item['file'], "rb") as video_file:
                        st.download_button(
                            label="📥 MP4",
                            data=video_file,
                            file_name=os.path.basename(item['file']),
                            mime="video/mp4",
                            key=f"dl_mp4_{idx}",
                            use_container_width=True
                        )
            
            st.markdown("---")
            
            # AI Processing button
            if st.button(
                f"✨ Run AI Production (Gemini 2.0)",
                key=f"run_{idx}",
                use_container_width=True,
                type="primary"
            ):
                res_area = st.empty()
                full_response = ""
                
                with st.status("🧠 Gemini 2.0 Processing...", expanded=True) as ai_status:
                    try:
                        # Upload
                        st.write("📤 Uploading video to Gemini...")
                        file_up = client.files.upload(file=item['file'])
                        
                        # Wait for processing
                        st.write("⏳ Waiting for Gemini to process...")
                        while file_up.state == "PROCESSING":
                            time.sleep(3)
                            file_up = client.files.get(name=file_up.name)
                        
                        if file_up.state == "FAILED":
                            st.error("❌ Gemini processing failed")
                            ai_status.update(label="❌ Failed", state="error")
                            continue
                        
                        # Configure for 65K tokens
                        st.write("✍️ Generating transcript and POV novel...")
                        
                        # UPDATED MODEL LIST: Prioritize Gemini 2.0
                        models_to_try = [
                            "gemini-2.0-flash",               # Latest Stable V2 (Fast & Capable)
                            "gemini-2.0-flash-thinking-exp",  # Thinking model (Great for Novels)
                            "gemini-1.5-pro",                 # Fallback (Robust)
                        ]
                        
                        response_generated = False
                        last_error = None
                        
                        for model_name in models_to_try:
                            try:
                                st.write(f"🤖 Trying model: {model_name}...")
                                
                                config = types.GenerateContentConfig(
                                    max_output_tokens=65000,
                                    temperature=0.7,
                                    tools=[types.Tool(google_search=types.GoogleSearch())]
                                )
                        
                                # Enhanced prompt for long POV chapters
                                prompt = f"""You are a professional TV script writer and novelist.

**CONTEXT:**
- Show: {item['show']}
- Cast: {item['cast']}
- Narrator POV: {item['pov']}

**TASK 1: VERBATIM TRANSCRIPT**
Create a complete, word-for-word transcript of the video.
- Identify each speaker using the cast list
- Format: CHARACTER_NAME: dialogue text
- Be 100% accurate - no paraphrasing
- Include ALL dialogue from start to finish

**TASK 2: DEEP POV NOVEL CHAPTER (MINIMUM 2500 WORDS)**
Write an immersive first-person novel chapter from {item['pov']}'s perspective.

REQUIREMENTS:
- Length: 2500+ words (this is CRITICAL - make it LONG and detailed)
- POV: First-person ("I", "me", "my") from {item['pov']}'s viewpoint
- Tense: Present tense for immediacy
- Style: Literary fiction, sensory-rich, cinematic

INCLUDE:
- Internal monologue and thoughts
- Emotional reactions and psychological depth
- Sensory details (sight, sound, smell, touch, taste)
- Environmental descriptions
- Character observations
- Backstory and memories (when relevant)
- Detailed scene-by-scene narrative
- Rich character voice

EXPAND EVERY SCENE:
- Don't rush through moments
- Add contemplation and reflection
- Describe body language and micro-expressions
- Show internal conflict
- Build atmosphere and tension
- Make every moment immersive

**OUTPUT FORMAT:**
Use these exact markers:

[TRANSCRIPT]
(complete verbatim transcript with speaker labels)
[END_TRANSCRIPT]

[NOVEL]
(deep POV novel chapter - MINIMUM 2500 WORDS - make it long, detailed, and immersive)
[END_NOVEL]

Remember: The novel chapter MUST be at least 2500 words. Use all available tokens to create a rich, detailed narrative."""
                        
                                # Streaming generation with current model
                                response = client.models.generate_content_stream(
                                    model=model_name,
                                    contents=[file_up, prompt],
                                    config=config
                                )
                                
                                # Collect chunks
                                for chunk in response:
                                    if hasattr(chunk, 'text') and chunk.text:
                                        full_response += chunk.text
                                        word_count = len(full_response.split())
                                        res_area.write(f"✍️ Generating... {word_count:,} words")
                                
                                # Success!
                                response_generated = True
                                st.success(f"✅ Used model: {model_name}")
                                break  # Exit loop on success
                                
                            except Exception as model_error:
                                last_error = str(model_error)
                                if "404" in last_error or "NOT_FOUND" in last_error:
                                    st.warning(f"⚠️ Model {model_name} not available, trying next...")
                                    continue  # Try next model
                                else:
                                    st.warning(f"⚠️ Error with {model_name}: {model_error}")
                                    continue
                        
                        if not response_generated:
                            raise Exception(f"All models failed. Last error: {last_error}")
                        
                        # Save
                        st.session_state[f"res_{idx}"] = full_response
                        
                        final_word_count = len(full_response.split())
                        ai_status.update(
                            label=f"✅ Complete! {final_word_count:,} words generated",
                            state="complete"
                        )
                        st.success("✅ AI Production finished!")
                        st.rerun()
                        
                    except Exception as e:
                        ai_status.update(label="❌ Error", state="error")
                        st.error(f"AI Error: {str(e)}")
            
            # Display results
            if f"res_{idx}" in st.session_state:
                raw = st.session_state[f"res_{idx}"]
                
                # Parse
                try:
                    transcript = raw.split("[TRANSCRIPT]")[1].split("[END_TRANSCRIPT]")[0].strip()
                    novel = raw.split("[NOVEL]")[1].split("[END_NOVEL]")[0].strip()
                except:
                    transcript = raw
                    novel = "⚠️ Could not parse novel. See transcript box."
                
                # Display
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📜 Verbatim Transcript")
                    st.text_area(
                        "Transcript",
                        transcript,
                        height=500,
                        key=f"t_{idx}"
                    )
                    
                    # Downloads
                    docx_t = create_docx(transcript, "Transcript")
                    if docx_t:
                        st.download_button(
                            "📥 Transcript (.docx)",
                            docx_t,
                            file_name=f"Transcript_{idx}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_t_{idx}"
                        )
                    
                    st.download_button(
                        "📥 Transcript (.txt)",
                        transcript,
                        file_name=f"Transcript_{idx}.txt",
                        key=f"dl_t_txt_{idx}"
                    )
                
                with col2:
                    st.subheader(f"📖 {item['pov']}'s POV Novel")
                    
                    # Show word count
                    novel_word_count = len(novel.split())
                    if novel_word_count >= 2500:
                        st.success(f"✅ {novel_word_count:,} words (target: 2500+)")
                    else:
                        st.warning(f"⚠️ {novel_word_count:,} words (target was 2500+)")
                    
                    st.text_area(
                        f"{item['pov']}'s Perspective",
                        novel,
                        height=500,
                        key=f"n_{idx}"
                    )
                    
                    # Downloads
                    docx_n = create_docx(novel, f"{item['pov']} POV Novel")
                    if docx_n:
                        st.download_button(
                            f"📥 {item['pov']}'s Novel (.docx)",
                            docx_n,
                            file_name=f"Novel_{item['pov']}_{idx}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_n_{idx}"
                        )
                    
                    st.download_button(
                        f"📥 {item['pov']}'s Novel (.txt)",
                        novel,
                        file_name=f"Novel_{item['pov']}_{idx}.txt",
                        key=f"dl_n_txt_{idx}"
                    )

# ==================== FOOTER ====================
st.markdown("---")
st.caption("🎬 POV Studio 2026 | PlayOn-Style Recording + Gemini 2.0 AI (65K Tokens)")
