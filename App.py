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
# ---------------- MAIN UI ----------------

st.title("🎬 Cinematic POV Story Engine")

st.markdown(
    """
This app turns real scenes into a **YA-style POV novel chapter** using:

- **Whisper medium** for stable transcription  
- **Gemini** to listen, read, and (for uploads) watch video  
"""
)

tab_url, tab_upload, tab_notes, tab_downloader = st.tabs(
    ["🌐 URL (audio-only)", "📁 Upload (MP4 or audio)", "📝 Writer notes", "⬇️ Download URL video only"]
)

with tab_url:
    url_link = st.text_input("Paste streaming URL (DisneyNow, Disney+, YouTube, etc.):")

with tab_upload:
    upload_file = st.file_uploader(
        "Upload MP4 video or audio file",
        type=["mp4", "mov", "mkv", "mp3", "wav", "m4a", "aac"],
    )

with tab_notes:
    live_notes = st.text_area(
        "Director / writer notes (optional):",
        placeholder="Tone, themes, what to emphasise in the chapter...",
        height=150,
    )

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


# ---------------- PIPELINE ----------------

if st.button("🚀 Run full pipeline", use_container_width=True):
    if not url_link and not upload_file:
        st.error("Please provide a URL or upload a file.")
    else:
        with st.status("Running pipeline...", expanded=True) as status:
            try:
                clean_temp_files()
                st.session_state.has_video_upload = False

                # 1. Get audio (URL mode = audio only)
                status.update(label="⬇️ Getting media...", state="running")

                if url_link:
                    if "disneynow.com" in url_link.lower() and not cookie_file:
                        st.error("DisneyNow URLs require cookies.txt.")
                        st.stop()
                    audio_source_path = download_audio_from_url(url_link, cookie_file)

                else:
                    # Upload mode
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

                # 2. Extract audio
                status.update(label="🎧 Extracting audio...", state="running")
                audio_path = extract_audio(audio_source_path)

                # 3. Whisper transcription
                status.update(label="📝 Transcribing with Whisper medium...", state="running")
                transcript_raw = whisper_transcribe(audio_path)
                st.session_state.transcript_raw = transcript_raw

                # 4. Gemini model
                model = get_gemini_model()
                safety = get_safety_settings()

                # 5. Upload media to Gemini
                status.update(label="📤 Uploading media to Gemini...", state="running")
                audio_file_obj = None
                video_file_obj = None

                if url_link:
                    audio_file_obj = upload_file_to_gemini(audio_path)
                else:
                    ext = os.path.splitext(upload_file.name)[1].lower()
                    if ext in [".mp4", ".mov", ".mkv"]:
                        video_file_obj = upload_file_to_gemini("temp_video_upload.mp4")
                    else:
                        audio_file_obj = upload_file_to_gemini(audio_path)

                # 6. Plot summary
                status.update(label="📚 Generating plot summary...", state="running")

                plot_inputs = []
                if video_file_obj:
                    plot_inputs.append(video_file_obj)
                if audio_file_obj:
                    plot_inputs.append(audio_file_obj)

                plot_prompt = f"""
CAST:
{cast_info}

TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
Write a clear plot summary of the scene.
"""

                if plot_inputs:
                    plot_inputs.append(plot_prompt)
                    plot_resp = model.generate_content(contents=plot_inputs, safety_settings=safety)
                else:
                    plot_resp = model.generate_content(contents=plot_prompt, safety_settings=safety)

                st.session_state.plot_summary = plot_resp.text.strip()

                # 7. Speaker tagging
                status.update(label="🎙️ Tagging speakers...", state="running")

                speaker_prompt = f"""
CAST:
{cast_info}

SUMMARY:
{st.session_state.plot_summary}

TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
Rewrite transcript with speaker tags.
"""

                speaker_resp = model.generate_content(contents=speaker_prompt, safety_settings=safety)
                st.session_state.transcript_tagged = speaker_resp.text.strip()

                # 8. Chapter
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
{live_notes}

TAGGED TRANSCRIPT:
\"\"\"{st.session_state.transcript_tagged}\"\"\"

TASK:
Write a YA-style POV chapter (~2500 words).
"""

                novel_resp = model.generate_content(contents=novel_prompt, safety_settings=safety)
                st.session_state.chapter = novel_resp.text.strip()

                st.session_state.processed = True
                status.update(label="✅ Done!", state="complete")
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                clean_temp_files()

    st.header("🌐 URL cookies")
    cookie_file = st.file_uploader("cookies.txt (required for DisneyNow)", type=["txt"])

    st.divider()
    if st.button("🗑️ Reset project"):
        for key in ["transcript_raw", "plot_summary", "transcript_tagged", "chapter", "processed", "has_video_upload"]:
            st.session_state[key] = "" if key not in ["processed", "has_video_upload"] else False
        clean_temp_files()
        st.rerun()
# ---------------- RESULTS ----------------

if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📚 Plot summary")
        st.text_area("Summary", st.session_state.plot_summary, height=200)

        st.subheader("📜 Transcript (speaker-tagged)")
        st.text_area("Transcript", st.session_state.transcript_tagged, height=300)

        st.download_button(
            "📥 Download transcript (Word)",
            create_docx("Transcript", st.session_state.transcript_tagged),
            "Transcript.docx",
        )

    with col2:
        st.subheader(f"📖 Novel chapter – {pov_choice} POV")
        st.text_area("Chapter", st.session_state.chapter, height=500)

        st.download_button(
            "📥 Download chapter (Word)",
            create_docx(f"{pov_choice} Chapter", st.session_state.chapter),
            "NovelChapter.docx",
        )

        if st.session_state.has_video_upload and os.path.exists("temp_video_upload.mp4"):
            st.markdown("### 🎞️ Uploaded video")
            with open("temp_video_upload.mp4", "rb") as f:
                st.download_button(
                    "Download uploaded video (MP4)",
                    f,
                    file_name="uploaded_scene.mp4",
                    mime="video/mp4",
                )
