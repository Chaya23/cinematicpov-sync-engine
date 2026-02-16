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
    ("has_video_url", False),
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
        {
            "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "threshold": HarmBlockThreshold.BLOCK_NONE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "threshold": HarmBlockThreshold.BLOCK_NONE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "threshold": HarmBlockThreshold.BLOCK_NONE,
        },
        {
            "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            "threshold": HarmBlockThreshold.BLOCK_NONE,
        },
    ]


def clean_temp_files():
    for f in [
        "temp_audio_source",
        "temp_audio.mp3",
        "temp_video_url.mp4",
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
    # STABLE: medium model
    model = whisper.load_model("medium")
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()


def get_gemini_model():
    models = [
        m.name
        for m in genai.list_models()
        if hasattr(m, "supported_generation_methods")
        and "generateContent" in m.supported_generation_methods
    ]
    flash = [m for m in models if "flash" in m.lower()]
    name = flash[0] if flash else "models/gemini-1.5-flash"
    return genai.GenerativeModel(name)


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


def download_media_from_url(url: str, cookie_file):
    audio_out = "temp_audio_source"
    video_out = "temp_video_url.mp4"

    for f in [audio_out, video_out]:
        if os.path.exists(f):
            os.remove(f)

    # audio
    cmd_audio = ["yt-dlp", "-f", "bestaudio", "-o", audio_out]
    if cookie_file:
        with open("cookies.txt", "wb") as f:
            f.write(cookie_file.getbuffer())
        cmd_audio.extend(["--cookies", "cookies.txt"])
    cmd_audio.append(url)
    subprocess.run(cmd_audio, check=True)

    # video (for user download only)
    cmd_video = [
        "yt-dlp",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "-o",
        video_out,
    ]
    if cookie_file:
        cmd_video.extend(["--cookies", "cookies.txt"])
    cmd_video.append(url)
    try:
        subprocess.run(cmd_video, check=True)
        st.session_state.has_video_url = True
    except subprocess.CalledProcessError:
        st.session_state.has_video_url = False

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
    cast_names = []
    for line in cast_lines:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name:
                cast_names.append(name)

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

    st.header("🌐 URL cookies")
    cookie_file = st.file_uploader("cookies.txt (required for DisneyNow)", type=["txt"])

    st.divider()
    if st.button("🗑️ Reset project"):
        for key in [
            "transcript_raw",
            "plot_summary",
            "transcript_tagged",
            "chapter",
            "processed",
            "has_video_url",
            "has_video_upload",
        ]:
            st.session_state[key] = "" if key not in ["processed", "has_video_url", "has_video_upload"] else False
        clean_temp_files()
        st.rerun()


# ---------------- MAIN UI ----------------

st.title("🎬 Cinematic POV Story Engine")

st.markdown(
    """
This app turns real scenes into a **YA-style POV novel chapter** using:

- **Whisper medium** for high-accuracy, stable transcription  
- **Gemini** to listen, read, and (for your uploads) watch video  
"""
)

with st.expander("📖 How to use this app"):
    st.markdown(
        """
### 1️⃣ Set up characters and POV (left sidebar)
- Edit the **Character list** to match your show.
- Choose a **POV narrator** or type a custom name.
- Pick **focus characters** for the chapter.

### 2️⃣ Tabs

**🌐 URL (streaming)**  
- Paste DisneyNow / Disney+ / YouTube etc.  
- App downloads:
  - audio → Whisper → Gemini  
  - MP4 → for you to save  

**📁 Upload (MP4 or audio)**  
- Upload:
  - MP4 / MOV / MKV (screen recordings, PlayOn, YouTube downloads)  
  - MP3 / WAV / M4A / AAC (audio only)  
- If MP4:
  - Whisper transcribes  
  - Gemini watches video + reads transcript  

**📝 Writer notes**  
- Add tone, themes, what to emphasise.

**⬇️ Download URL video only**  
- Pure downloader: URL + cookies.txt → MP4 file for your phone.  
- Later you can upload that MP4 in the Upload tab.

### 3️⃣ Run the pipeline
Click **“🚀 Run full pipeline”** to generate:
- Plot summary  
- Speaker-tagged transcript  
- POV chapter  
"""
    )

with st.expander("ℹ️ How to get cookies.txt for DisneyNow (URL mode)"):
    st.markdown(
        """
DisneyNow uses short‑lived security tokens. To download audio/video from DisneyNow URLs, you **must** provide a `cookies.txt` file from your own device.

If downloads fail, export a fresh `cookies.txt` or use the **Download URL video only** tab and then upload the saved MP4 in the Upload tab.
"""
    )

tab_url, tab_upload, tab_notes, tab_downloader = st.tabs(
    ["🌐 URL (streaming)", "📁 Upload (MP4 or audio)", "📝 Writer notes", "⬇️ Download URL video only"]
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
    dl_url = st.text_input("Streaming URL (DisneyNow, Disney+, Netflix, etc.)", key="dl_url")
    dl_cookies = st.file_uploader("cookies.txt (required for most streaming sites)", type=["txt"], key="dl_cookies")

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
                    st.success("Download complete. Use the button below to save the file to your device.")
                    with open(out_path, "rb") as f:
                        st.download_button(
                            "📥 Save video file (MP4)",
                            f,
                            file_name="stream_capture.mp4",
                            mime="video/mp4",
                        )
                else:
                    st.error("Download finished but file not found. Try again or check the URL/cookies.")

            except subprocess.CalledProcessError as e:
                st.error(f"yt-dlp error:\n{e}\n\nCheck cookies.txt or try another URL.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")


# ---------------- PIPELINE ----------------

if st.button("🚀 Run full pipeline", use_container_width=True):
    if not url_link and not upload_file:
        st.error("Please provide a URL or upload a file.")
    else:
        with st.status("Running pipeline...", expanded=True) as status:
            try:
                clean_temp_files()
                st.session_state.has_video_url = False
                st.session_state.has_video_upload = False

                # 1. Get audio (and video) depending on mode
                status.update(label="⬇️ Getting media...", state="running")

                audio_source_path = None
                upload_video_path = None

                if url_link:
                    # URL MODE
                    if "disneynow.com" in url_link.lower() and not cookie_file:
                        st.error("DisneyNow URLs require cookies.txt. Upload it in the sidebar.")
                        clean_temp_files()
                        st.stop()
                    try:
                        audio_source_path = download_media_from_url(url_link, cookie_file)
                    except subprocess.CalledProcessError as e:
                        st.error(
                            f"yt-dlp failed.\n\n{e}\n\n"
                            "For DisneyNow/Disney+, check cookies.txt or use the Upload tab with a recording."
                        )
                        clean_temp_files()
                        st.stop()
                else:
                    # UPLOAD MODE
                    if upload_file is None:
                        st.error("No file uploaded.")
                        clean_temp_files()
                        st.stop()

                    ext = os.path.splitext(upload_file.name)[1].lower()
                    if ext in [".mp4", ".mov", ".mkv"]:
                        upload_video_path = "temp_video_upload.mp4"
                        with open(upload_video_path, "wb") as f:
                            f.write(upload_file.getbuffer())
                        st.session_state.has_video_upload = True
                        audio_source_path = upload_video_path
                    else:
                        audio_source_path = "temp_audio_source"
                        with open(audio_source_path, "wb") as f:
                            f.write(upload_file.getbuffer())

                # 2. Extract audio to MP3
                status.update(label="🎧 Extracting audio...", state="running")
                audio_path = extract_audio(audio_source_path, "temp_audio.mp3")

                # 3. Whisper transcription
                status.update(label="📝 Transcribing with Whisper medium...", state="running")
                transcript_raw = whisper_transcribe(audio_path)
                if not transcript_raw or len(transcript_raw) < 50:
                    st.error("Transcript is empty or too short. Try a different clip.")
                    clean_temp_files()
                    st.stop()
                st.session_state.transcript_raw = transcript_raw

                # 4. Gemini model + safety
                model = get_gemini_model()
                safety = get_safety_settings()

                # 5. Upload media to Gemini
                status.update(label="📤 Uploading media to Gemini...", state="running")
                audio_file_obj = None
                video_file_obj = None

                # URL mode: audio only
                if url_link:
                    audio_file_obj = upload_file_to_gemini(audio_path)
                else:
                    # Upload mode
                    ext = os.path.splitext(upload_file.name)[1].lower()
                    if ext in [".mp4", ".mov", ".mkv"]:
                        # B: MP4 video + transcript (no separate audio file)
                        video_file_obj = upload_file_to_gemini("temp_video_upload.mp4")
                    else:
                        audio_file_obj = upload_file_to_gemini(audio_path)

                # 6. Plot summary
                status.update(label="📚 Generating plot summary...", state="running")

                plot_inputs = []
                if video_file_obj is not None:
                    plot_inputs.append(video_file_obj)
                if audio_file_obj is not None:
                    plot_inputs.append(audio_file_obj)

                plot_prompt = f"""
You are a story analyst.

CAST (name: role):
{cast_info}

RAW TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
1. Use the media (video/audio if provided) and the transcript.
2. Produce a clear plot summary of what happens in this scene.
3. Mention key characters, relationships, conflicts, and emotional beats.
4. Keep it 3–8 paragraphs, no bullet points, no meta commentary.
"""

                if plot_inputs:
                    plot_inputs.append(plot_prompt)
                    plot_resp = model.generate_content(
                        contents=plot_inputs,
                        safety_settings=safety,
                    )
                else:
                    plot_resp = model.generate_content(
                        contents=plot_prompt,
                        safety_settings=safety,
                    )

                plot_summary = (plot_resp.text or "").strip() if plot_resp else ""
                st.session_state.plot_summary = plot_summary

                # 7. Speaker tagging
                status.update(label="🎙️ Tagging speakers...", state="running")

                speaker_prompt = f"""
You are a careful dialogue editor.

CAST (name: role):
{cast_info}

PLOT SUMMARY:
\"\"\"{plot_summary}\"\"\"

RAW TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
1. Rewrite the transcript as clean dialogue lines.
2. For each line of speech, tag the speaker using the character names from the cast list when possible.
   - Format: "Roman: I don't know if I can do this."
   - If you're not sure, use "Unknown:" but try to infer from context and the plot summary.
3. Keep wording close to the original, only fixing obvious transcription errors.
4. Preserve line breaks. Do NOT summarise. Do NOT add commentary.
"""

                speaker_resp = model.generate_content(
                    contents=speaker_prompt,
                    safety_settings=safety,
                )
                transcript_tagged = (speaker_resp.text or "").strip() if speaker_resp else ""
                if not transcript_tagged or len(transcript_tagged) < 50:
                    transcript_tagged = transcript_raw
                st.session_state.transcript_tagged = transcript_tagged

                # 8. YA POV chapter
                status.update(label="📖 Writing YA-style POV chapter...", state="running")

                focus_str = ", ".join(focus_characters) if focus_characters else "all characters"

                novel_prompt = f"""
You are a skilled YA novelist.

CAST (name: role):
{cast_info}

PLOT SUMMARY:
\"\"\"{plot_summary}\"\"\"

PRIMARY NARRATOR POV:
{pov_choice}

FOCUS CHARACTERS:
{focus_str}

DIRECTOR / WRITER NOTES:
{live_notes}

SOURCE TRANSCRIPT (each line tagged with speaker):
\"\"\"{transcript_tagged}\"\"\"

TASK:
Using the tagged transcript and plot summary as the backbone, write a ~2500-word YA-style novel chapter.

REQUIREMENTS:
- First-person POV from {pov_choice}.
- Show rich internal thoughts, emotions, and reactions of {pov_choice}.
- Use the speaker tags to keep who-said-what consistent with the transcript.
- Include interactions and dialogue with the other characters, especially: {focus_str}.
- Keep the tone grounded, emotional, and character-driven, like a young adult contemporary / drama.
- Preserve the key events and emotional beats from the plot summary and transcript, but you may add internal monologue, sensory detail, and subtle expansions.
- Make Giada explicitly the mother if she appears.
- Do NOT include analysis, explanation, or meta-commentary. Output ONLY the story text.
"""

                novel_resp = model.generate_content(
                    contents=novel_prompt,
                    safety_settings=safety,
                )
                chapter_text = (novel_resp.text or "").strip() if novel_resp else ""
                if not chapter_text or len(chapter_text) < 100:
                    st.error("Gemini returned an empty or very short chapter. Try a different clip.")
                    clean_temp_files()
                    st.stop()

                st.session_state.chapter = chapter_text
                st.session_state.processed = True

                status.update(label="✅ Done! Results ready below.", state="complete")
                clean_temp_files()
                st.rerun()

            except subprocess.CalledProcessError as e:
                st.error(f"Download / ffmpeg error: {e}")
                clean_temp_files()
            except Exception as e:
                st.error(f"Error: {e}")
                clean_temp_files()


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

        st.markdown("### 🎞️ Video downloads (if available)")
        if st.session_state.has_video_url and os.path.exists("temp_video_url.mp4"):
            with open("temp_video_url.mp4", "rb") as f:
                st.download_button(
                    "Download URL video (MP4)",
                    f,
                    file_name="scene_url.mp4",
                    mime="video/mp4",
                )
        if st.session_state.has_video_upload and os.path.exists("temp_video_upload.mp4"):
            with open("temp_video_upload.mp4", "rb") as f:
                st.download_button(
                    "Download uploaded video (MP4)",
                    f,
                    file_name="scene_upload.mp4",
                    mime="video/mp4",
                )
