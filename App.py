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

# Gemini API key (set in Streamlit secrets)
api_key = st.secrets.get("GEMINI_API_KEY", "")
api_key = api_key.strip() if api_key else ""
if not api_key:
    st.error("🔑 Gemini API key missing. Add GEMINI_API_KEY to Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)

# Session state
for key, default in [
    ("transcript_raw", ""),
    ("plot_summary", ""),
    ("transcript_tagged", ""),
    ("chapter", ""),
    ("processed", False),
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
    for f in ["temp_video.mp4", "temp_audio.mp3", "cookies.txt"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def extract_audio(video_path: str, audio_path: str = "temp_audio.mp3") -> str:
    if os.path.exists(audio_path):
        os.remove(audio_path)
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", audio_path]
    subprocess.run(cmd, check=True)
    return audio_path


def whisper_transcribe(audio_path: str) -> str:
    # You can change "base" to "small" / "medium" / "large" if your server is stronger
    model = whisper.load_model("base")
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


def upload_audio_to_gemini(audio_path: str):
    try:
        file_obj = genai.upload_file(path=audio_path)
        # Wait until processed
        while getattr(file_obj, "state", None) and file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        if getattr(file_obj, "state", None) and file_obj.state.name == "FAILED":
            return None
        return file_obj
    except Exception:
        return None


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.header("🎭 Character Bible")
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

    st.header("👤 POV & Focus")
    pov_options = ["Custom"] + cast_names
    pov_choice = st.selectbox("Primary POV narrator:", pov_options)
    if pov_choice == "Custom":
        pov_choice = st.text_input("Custom POV name:", value="Roman Russo")

    focus_characters = st.multiselect(
        "Focus characters:",
        options=cast_names,
        default=cast_names,
    )

    st.header("🌐 Download options")
    cookie_file = st.file_uploader("cookies.txt (optional, for Disney/region)", type=["txt"])
    geo_bypass = st.checkbox("Force geo-bypass (US)", value=True)

    st.divider()
    if st.button("🗑️ Reset project"):
        for key in ["transcript_raw", "plot_summary", "transcript_tagged", "chapter", "processed"]:
            st.session_state[key] = "" if key != "processed" else False
        clean_temp_files()
        st.rerun()


# ---------------- MAIN UI ----------------

st.title("🎬 Cinematic POV Story Engine")
st.write(
    "Upload a video or paste a streaming URL. The app will transcribe the audio, "
    "summarise the plot, tag who said what using your cast list, and write a YA-style "
    "novel chapter from your chosen POV."
)

tab_file, tab_url, tab_notes = st.tabs(["📁 File upload", "🌐 URL input", "📝 Live notes"])

with tab_file:
    file_vid = st.file_uploader("Upload MP4/MOV (PlayOn, YouTube downloads, etc.)", type=["mp4", "mov"])

with tab_url:
    url_link = st.text_input("Paste video URL (Disney+, DisneyNow, YouTube, etc.):")

with tab_notes:
    live_notes = st.text_area(
        "Director / writer notes (optional):",
        placeholder="Tone, themes, what to emphasise in the chapter...",
        height=150,
    )


# ---------------- PIPELINE BUTTON ----------------

if st.button("🚀 Run full pipeline", use_container_width=True):
    if not file_vid and not url_link:
        st.error("Please upload a video file or provide a URL.")
    else:
        with st.status("Running Whisper + Gemini pipeline...", expanded=True) as status:
            try:
                clean_temp_files()
                source = "temp_video.mp4"

                # 1. Download or save video
                status.update(label="⬇️ Downloading / saving video...", state="running")
                if file_vid:
                    with open(source, "wb") as f:
                        f.write(file_vid.getbuffer())
                else:
                    cmd = ["yt-dlp", "-f", "best", "-o", source]
                    if geo_bypass:
                        cmd.extend(["--geo-bypass", "--geo-bypass-country", "US"])
                    if cookie_file:
                        with open("cookies.txt", "wb") as f:
                            f.write(cookie_file.getbuffer())
                        cmd.extend(["--cookies", "cookies.txt"])
                    cmd.append(url_link)
                    subprocess.run(cmd, check=True)

                # 2. Extract audio
                status.update(label="🎧 Extracting audio with ffmpeg...", state="running")
                audio_path = extract_audio(source)

                # 3. Whisper transcription
                status.update(label="📝 Transcribing audio with Whisper...", state="running")
                transcript_raw = whisper_transcribe(audio_path)
                if not transcript_raw or len(transcript_raw) < 50:
                    st.error("Transcript is empty or too short. Check the audio or try another video.")
                    clean_temp_files()
                    st.stop()
                st.session_state.transcript_raw = transcript_raw

                # 4. Gemini model
                model = get_gemini_model()
                safety = get_safety_settings()

                # 5. Upload audio to Gemini (for non-DRM / when possible)
                status.update(label="📤 Uploading audio to Gemini (if supported)...", state="running")
                audio_file_obj = upload_audio_to_gemini(audio_path)

                # 6. Plot summary (Gemini listens + reads when possible)
                status.update(label="📚 Generating plot summary...", state="running")

                if audio_file_obj is not None:
                    plot_prompt_input = [
                        audio_file_obj,
                        f"""
You are a story analyst.

CAST (name: role):
{cast_info}

RAW TRANSCRIPT:
\"\"\"{transcript_raw}\"\"\"

TASK:
1. Listen to the audio and read the transcript.
2. Produce a clear plot summary of what happens in the video.
3. Mention key characters, relationships, conflicts, and emotional beats.
4. Keep it 3–8 paragraphs, no bullet points, no meta commentary.
""",
                    ]
                else:
                    plot_prompt_input = f"""
You are a story analyst.

CAST (name: role):
{cast_info}

RAW TRANSCRIPT (audio could not be provided, so rely on text only):
\"\"\"{transcript_raw}\"\"\"

TASK:
1. Produce a clear plot summary of what happens in the video.
2. Mention key characters, relationships, conflicts, and emotional beats.
3. Keep it 3–8 paragraphs, no bullet points, no meta commentary.
"""

                plot_resp = model.generate_content(
                    contents=plot_prompt_input,
                    safety_settings=safety,
                )
                plot_summary = (plot_resp.text or "").strip() if plot_resp else ""
                st.session_state.plot_summary = plot_summary

                # 7. Speaker tagging using plot + cast + transcript
                status.update(label="🎙️ Tagging who said what (speaker names)...", state="running")

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

                # 8. YA POV novel chapter
                status.update(label="📖 Writing YA-style POV novel chapter...", state="running")

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
                    st.error("Gemini returned an empty or very short chapter. Try a different video or shorter content.")
                    clean_temp_files()
                    st.stop()

                st.session_state.chapter = chapter_text
                st.session_state.processed = True

                status.update(label="✅ Done! Transcript, plot, speakers, and chapter ready.", state="complete")
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
        st.subheader(f"📖 Novel chapter – {pov_choice} POV (YA-style)")
        st.text_area("Chapter", st.session_state.chapter, height=500)

        st.download_button(
            "📥 Download chapter (Word)",
            create_docx(f"{pov_choice} Chapter", st.session_state.chapter),
            "NovelChapter.docx",
        )
 
