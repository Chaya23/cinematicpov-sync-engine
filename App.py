import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import subprocess
import os
import time
from io import BytesIO
from docx import Document
import whisper

# ---------------- CONFIG ----------------

st.set_page_config(page_title="Cinematic POV Story Engine", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "")
api_key = api_key.strip() if api_key else ""
if not api_key:
    st.error("🔑 Gemini API key missing. Add GEMINI_API_KEY to Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)

# Session state defaults
for key, default in [
    ("transcript_raw", ""),
    ("plot_summary", ""),
    ("transcript_tagged", ""),
    ("chapter", ""),
    ("processed", False),
    ("has_video_upload", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------- HELPERS ----------------

def create_docx(title: str, content: str) -> bytes:
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split("\n"):
        doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()


def get_safety_settings():
    return [
        {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
        {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
        {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
        {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    ]


def clean_temp_files():
    for f in [
        "temp_audio_source",
        "temp_audio.mp3",
        "temp_video_upload.mp4",
        "downloaded_url_video.mp4",
        "cookies.txt",
    ]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def extract_audio(input_path: str, audio_path: str = "temp_audio.mp3") -> str:
    if os.path.exists(audio_path):
        os.remove(audio_path)
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "mp3", audio_path]
    subprocess.run(cmd, check=True)
    return audio_path


def whisper_transcribe(audio_path: str) -> str:
    model = whisper.load_model("medium")
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()


def get_gemini_model():
    models = [
        m.name for m in genai.list_models()
        if hasattr(m, "supported_generation_methods")
        and "generateContent" in m.supported_generation_methods
    ]
    flash = [m for m in models if "flash" in m.lower()]
    return genai.GenerativeModel(flash[0] if flash else "models/gemini-1.5-flash")


def upload_file_to_gemini(path: str):
    try:
        file_obj = genai.upload_file(path=path)
        while getattr(file_obj, "state", None) and file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        if getattr(file_obj, "state", None) and file_obj.state.name == "FAILED":
            return None
        return file_obj
    except Exception:
        return None


def download_audio_from_url(url: str, cookie_file):
    audio_out = "temp_audio_source"
    if os.path.exists(audio_out):
        os.remove(audio_out)

    cmd = ["yt-dlp", "-f", "bestaudio", "-o", audio_out]

    if cookie_file:
        with open("cookies.txt", "wb") as f:
            f.write(cookie_file.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])

    cmd.append(url)
    subprocess.run(cmd, check=True)
    return audio_out
# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.header("🎭 Character list")
    cast_info = st.text_area(
        "Cast list (name: role):",
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother",
        height=150,
    )

    cast_lines = [line.strip() for line in cast_info.splitlines() if line.strip()]
    cast_names = [line.split(":", 1)[0].strip() for line in cast_lines if ":" in line]

    st.header("👤 POV & focus")
    pov_options = ["Custom"] + cast_names
    pov_choice = st.selectbox("Primary POV narrator:", pov_options)
    if pov_choice == "Custom":
        pov_choice = st.text_input("Custom POV name:", value="Roman Russo")

    focus_characters = st.multiselect(
        "Focus characters:",
        options=cast_names,
        default=cast_names,
    )

    st.header("🌐 URL cookies (desktop mode)")
    cookie_file = st.file_uploader("cookies.txt (required for DisneyNow)", type=["txt"])

    st.divider()
    if st.button("🗑️ Reset project"):
        for key in ["transcript_raw", "plot_summary", "transcript_tagged", "chapter", "processed", "has_video_upload"]:
            st.session_state[key] = "" if key not in ["processed", "has_video_upload"] else False
        clean_temp_files()
        st.rerun()


# ---------------- MODE TOGGLE ----------------

st.title("🎬 Cinematic POV Story Engine")

mode = st.radio(
    "Choose mode:",
    ["Mobile (light)", "Desktop (full)"],
    horizontal=True
)

st.markdown(
    """
### 📱 Mobile (light)
- Upload **MP4 or audio**
- Gemini **watches video**, extracts audio, **transcribes**, summarizes, tags speakers, writes novel  
- **One‑pass pipeline**  
- **No Whisper**, **no ffmpeg**, **no yt‑dlp**  
- Designed to avoid mobile crashes  

### 💻 Desktop (full)
- URL extraction (DisneyNow, Disney+, YouTube)  
- **cookies.txt** support  
- yt‑dlp extracts **audio only**  
- Upload MP4 or audio  
- Gemini can watch uploaded MP4s  
- **Dropdown to choose transcription method:** Whisper or Gemini  
- Downloader tab (MP4 only)  
"""
)
# ---------------- MOBILE MODE (LIGHT) ----------------

if mode == "Mobile (light)":
    st.subheader("📱 Mobile Mode — Gemini-only (MP4-safe, no Whisper, no yt‑dlp)")

    mobile_file = st.file_uploader(
        "Upload MP4 or audio (Gemini will watch/listen and do everything)",
        type=["mp4", "mov", "mkv", "mp3", "wav", "m4a", "aac"],
    )

    mobile_notes = st.text_area(
        "Director / writer notes (optional):",
        placeholder="Tone, themes, emotions, pacing, etc.",
        height=150,
    )

    if st.button("🚀 Run Mobile Pipeline", use_container_width=True):
        if not mobile_file:
            st.error("Please upload a video or audio file.")
        else:
            with st.status("Running Gemini one‑pass pipeline...", expanded=True) as status:
                try:
                    clean_temp_files()

                    # Save uploaded file
                    temp_path = "temp_mobile_upload"
                    with open(temp_path, "wb") as f:
                        f.write(mobile_file.getbuffer())

                    status.update(label="📤 Uploading media to Gemini...", state="running")
                    model = get_gemini_model()
                    safety = get_safety_settings()

                    gem_file = upload_file_to_gemini(temp_path)

                    if not gem_file:
                        st.error("Gemini could not process the uploaded file.")
                        st.stop()

                    status.update(label="🧠 Gemini watching video + transcribing + summarizing + tagging + writing novel...", state="running")

                    # ONE-PASS PROMPT
                    one_pass_prompt = f"""
You are a masterful multimodal AI who can watch video, extract audio, transcribe speech,
summarize events, identify speakers, and write a YA-style novel chapter.

CAST (name: role):
{cast_info}

PRIMARY POV:
{pov_choice}

FOCUS CHARACTERS:
{", ".join(focus_characters)}

DIRECTOR NOTES:
{mobile_notes}

TASK:
1. Watch/listen to the uploaded media.
2. Transcribe all dialogue.
3. Write a clear plot summary.
4. Rewrite the transcript with speaker tags using the cast list.
5. Write a ~2500-word YA-style novel chapter in FIRST PERSON from {pov_choice}.
6. Use emotional depth, internal thoughts, sensory detail, and character-driven pacing.
7. Keep Giada explicitly the mother if she appears.
8. Output ONLY the following sections:

[TRANSCRIPT]
(full raw transcript)

[SUMMARY]
(plot summary)

[TAGGED_TRANSCRIPT]
(transcript with speaker names)

[CHAPTER]
(full YA-style novel chapter)
"""

                    resp = model.generate_content(
                        contents=[gem_file, one_pass_prompt],
                        safety_settings=safety
                    )

                    full_text = (resp.text or "").strip()

                    # Parse sections
                    transcript_raw = ""
                    plot_summary = ""
                    transcript_tagged = ""
                    chapter_text = ""

                    current = None
                    for line in full_text.splitlines():
                        l = line.strip()
                        if l.upper().startswith("[TRANSCRIPT"):
                            current = "t"
                            continue
                        if l.upper().startswith("[SUMMARY"):
                            current = "s"
                            continue
                        if l.upper().startswith("[TAGGED_TRANSCRIPT"):
                            current = "tt"
                            continue
                        if l.upper().startswith("[CHAPTER"):
                            current = "c"
                            continue

                        if current == "t":
                            transcript_raw += line + "\n"
                        elif current == "s":
                            plot_summary += line + "\n"
                        elif current == "tt":
                            transcript_tagged += line + "\n"
                        elif current == "c":
                            chapter_text += line + "\n"

                    # Save to session
                    st.session_state.transcript_raw = transcript_raw.strip()
                    st.session_state.plot_summary = plot_summary.strip()
                    st.session_state.transcript_tagged = transcript_tagged.strip()
                    st.session_state.chapter = chapter_text.strip()
                    st.session_state.processed = True

                    status.update(label="✅ Mobile pipeline complete!", state="complete")
                    clean_temp_files()

                except Exception as e:
                    st.error(f"Error: {e}")
                    clean_temp_files()
# ---------------- DESKTOP MODE (FULL) ----------------

else:
    st.subheader("💻 Desktop Mode — Full Pipeline")

    tab_url, tab_upload, tab_notes, tab_downloader = st.tabs(
        ["🌐 URL (audio-only)", "📁 Upload (MP4 or audio)", "📝 Writer notes", "⬇️ Downloader (MP4 only)"]
    )

    # ---------------- URL TAB ----------------
    with tab_url:
        url_link = st.text_input("Paste streaming URL (DisneyNow, Disney+, YouTube, etc.):")

        transcription_method = st.selectbox(
            "Transcription method:",
            ["Whisper‑medium (local)", "Gemini (cloud transcription)"],
            index=0
        )

    # ---------------- UPLOAD TAB ----------------
    with tab_upload:
        upload_file = st.file_uploader(
            "Upload MP4 video or audio file",
            type=["mp4", "mov", "mkv", "mp3", "wav", "m4a", "aac"],
        )

    # ---------------- NOTES TAB ----------------
    with tab_notes:
        desktop_notes = st.text_area(
            "Director / writer notes (optional):",
            placeholder="Tone, themes, pacing, emotional beats...",
            height=150,
        )

    # ---------------- DOWNLOADER TAB ----------------
    with tab_downloader:
        st.subheader("Download streaming video to a file (no AI, just save it)")

        dl_url = st.text_input("Streaming URL", key="dl_url")
        dl_cookies = st.file_uploader("cookies.txt (required for many sites)", type=["txt"], key="dl_cookies")

        if st.button("🎞️ Download video file", key="dl_button"):
            if not dl_url:
                st.error("Please enter a URL.")
            else:
                try:
                    if dl_cookies:
                        with open("cookies.txt", "wb") as f:
                            f.write(dl_cookies.getbuffer())
                        cookies_args = ["--cookies", "cookies.txt"]
                    else:
                        cookies_args = []

                    out_path = "downloaded_url_video.mp4"
                    if os.path.exists(out_path):
                        os.remove(out_path)

                    cmd = [
                        "yt-dlp",
                        "-f",
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                        "-o",
                        out_path,
                    ] + cookies_args + [dl_url]

                    with st.spinner("Downloading with yt-dlp..."):
                        subprocess.run(cmd, check=True)

                    if os.path.exists(out_path):
                        st.success("Download complete. Save the file below.")
                        with open(out_path, "rb") as f:
                            st.download_button(
                                "📥 Save video file (MP4)",
                                f,
                                file_name="downloaded_video.mp4",
                                mime="video/mp4",
                            )
                    else:
                        st.error("Download finished but file not found.")

                except Exception as e:
                    st.error(f"Error: {e}")

    # ---------------- RUN DESKTOP PIPELINE ----------------

    if st.button("🚀 Run Desktop Pipeline", use_container_width=True):
        if not url_link and not upload_file:
            st.error("Please provide a URL or upload a file.")
        else:
            with st.status("Running desktop pipeline...", expanded=True) as status:
                try:
                    clean_temp_files()
                    st.session_state.has_video_upload = False

                    # 1. GET MEDIA (URL or upload)
                    status.update(label="⬇️ Getting media...", state="running")

                    if url_link:
                        if "disneynow.com" in url_link.lower() and not cookie_file:
                            st.error("DisneyNow URLs require cookies.txt.")
                            st.stop()

                        audio_source_path = download_audio_from_url(url_link, cookie_file)

                    else:
                        ext = os.path.splitext(upload_file.name)[1].lower()
                        if ext in [".mp4", ".mov", ".mkv"]:
                            video_path = "temp_video_upload.mp4"
                            with open(video_path, "wb") as f:
                                f.write(upload_file.getbuffer())
                            st.session_state.has_video_upload = True
                            audio_source_path = video_path
                        else:
                            audio_source_path = "temp_audio_source"
                            with open(audio_source_path, "wb") as f:
                                f.write(upload_file.getbuffer())

                    # 2. EXTRACT AUDIO (only if video)
                    status.update(label="🎧 Extracting audio...", state="running")

                    ext = os.path.splitext(audio_source_path)[1].lower()
                    if ext in [".mp4", ".mov", ".mkv"]:
                        audio_path = extract_audio(audio_source_path)
                    else:
                        audio_path = audio_source_path

                    # 3. TRANSCRIPTION (Whisper or Gemini)
                    status.update(label="📝 Transcribing...", state="running")

                    if transcription_method.startswith("Whisper"):
                        transcript_raw = whisper_transcribe(audio_path)

                    else:
                        model = get_gemini_model()
                        safety = get_safety_settings()
                        gem_audio = upload_file_to_gemini(audio_path)

                        trans_prompt = """
You are a careful transcriber. Transcribe the audio exactly as spoken.
Return ONLY the transcript.
"""
                        resp = model.generate_content(
                            contents=[gem_audio, trans_prompt],
                            safety_settings=safety
                        )
                        transcript_raw = (resp.text or "").strip()

                    st.session_state.transcript_raw = transcript_raw

                    # 4. GEMINI SUMMARY
                    status.update(label="📚 Generating plot summary...", state="running")

                    model = get_gemini_model()
                    safety = get_safety_settings()

                    summary_prompt = f"""
CAST:
{cast_info}

TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
Write a clear plot summary of the scene.
"""

                    summary_resp = model.generate_content(
                        contents=summary_prompt,
                        safety_settings=safety
                    )

                    st.session_state.plot_summary = summary_resp.text.strip()

                    # 5. SPEAKER TAGGING
                    status.update(label="🎙️ Tagging speakers...", state="running")

                    tag_prompt = f"""
CAST:
{cast_info}

SUMMARY:
{st.session_state.plot_summary}

TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
Rewrite transcript with speaker tags.
"""

                    tag_resp = model.generate_content(
                        contents=tag_prompt,
                        safety_settings=safety
                    )

                    st.session_state.transcript_tagged = tag_resp.text.strip()

                    # 6. NOVEL CHAPTER
                    status.update(label="📖 Writing YA-style POV chapter...", state="running")

                    focus_str = ", ".join(focus_characters)

                    novel_prompt = f"""
CAST:
{cast_info}

SUMMARY:
{st.session_state.plot_summary}

POV:
{pov_choice}

FOCUS:
{focus_str}

NOTES:
{desktop_notes}

TAGGED TRANSCRIPT:
\"\"\"{st.session_state.transcript_tagged}\"\"\"

TASK:
Write a YA-style POV chapter (~2500 words).
"""

                    novel_resp = model.generate_content(
                        contents=novel_prompt,
                        safety_settings=safety
                    )

                    st.session_state.chapter = novel_resp.text.strip()
                    st.session_state.processed = True

                    status.update(label="✅ Desktop pipeline complete!", state="complete")
                    clean_temp_files()

                except Exception as e:
                    st.error(f"Error: {e}")
                    clean_temp_files()
# ---------------- RESULTS (SHARED FOR BOTH MODES) ----------------

if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)

    # -------- LEFT COLUMN --------
    with col1:
        st.subheader("📚 Plot Summary")
        st.text_area(
            "Summary",
            st.session_state.plot_summary,
            height=200
        )

        st.subheader("📜 Transcript (Speaker‑Tagged)")
        st.text_area(
            "Transcript",
            st.session_state.transcript_tagged,
            height=300
        )

        st.download_button(
            "📥 Download Transcript (Word)",
            create_docx("Transcript", st.session_state.transcript_tagged),
            "Transcript.docx",
        )

    # -------- RIGHT COLUMN --------
    with col2:
        st.subheader(f"📖 Novel Chapter — {pov_choice} POV")
        st.text_area(
            "Chapter",
            st.session_state.chapter,
            height=500
        )

        st.download_button(
            "📥 Download Chapter (Word)",
            create_docx(f"{pov_choice} Chapter", st.session_state.chapter),
            "NovelChapter.docx",
        )

        # If user uploaded a video in desktop mode, allow them to download it back
        if st.session_state.has_video_upload and os.path.exists("temp_video_upload.mp4"):
            st.markdown("### 🎞️ Uploaded Video")
            with open("temp_video_upload.mp4", "rb") as f:
                st.download_button(
                    "Download Uploaded Video (MP4)",
                    f,
                    file_name="uploaded_scene.mp4",
                    mime="video/mp4",
                )
# ---------------- FOOTER / CLEANUP ----------------

st.markdown("---")
st.markdown(
    "Built with ❤️ using Streamlit, Whisper, yt‑dlp, and Gemini multimodal models."
)

# Final cleanup on rerun
clean_temp_files()
