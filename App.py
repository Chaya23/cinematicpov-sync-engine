import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import subprocess
from docx import Document
from io import BytesIO
import os
import whisper

# ---------- CONFIG ----------

st.set_page_config(page_title="Roman's Master Studio", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY", "")
api_key = api_key.strip() if api_key else ""
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

if "transcript_raw" not in st.session_state:
    st.session_state.transcript_raw = ""
if "transcript_tagged" not in st.session_state:
    st.session_state.transcript_tagged = ""
if "chapter" not in st.session_state:
    st.session_state.chapter = ""
if "processed" not in st.session_state:
    st.session_state.processed = False

# ---------- HELPERS ----------

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
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

def extract_audio(video_path, audio_path="temp_audio.mp3"):
    if os.path.exists(audio_path):
        os.remove(audio_path)
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", audio_path]
    subprocess.run(cmd, check=True)
    return audio_path

def whisper_transcribe(audio_path):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()

def get_gemini_model():
    available_models = [
        m.name
        for m in genai.list_models()
        if hasattr(m, "supported_generation_methods")
        and "generateContent" in m.supported_generation_methods
    ]
    flash_models = [m for m in available_models if "flash" in m.lower()]
    selected_model = flash_models[0] if flash_models else "models/gemini-1.5-flash"
    return genai.GenerativeModel(selected_model)

# ---------- SIDEBAR ----------

with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area(
        "Cast Roles (Editable):",
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother"
    )

    cast_lines = [line.strip() for line in cast_info.splitlines() if line.strip()]
    cast_names = []
    for line in cast_lines:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name:
                cast_names.append(name)

    st.header("👤 POV & Focus Characters")
    pov_options = ["Custom"] + cast_names
    pov_choice = st.selectbox("Primary Narrator POV:", pov_options)
    if pov_choice == "Custom":
        pov_choice = st.text_input("Enter Custom Narrator Name:", value="Roman Russo")

    focus_characters = st.multiselect(
        "Focus Characters (multi-select):",
        options=cast_names,
        default=cast_names
    )

    st.header("🌐 Bypass / Download")
    cookie_file = st.file_uploader("Upload cookies.txt (For Disney/Region bypass)", type=["txt"])
    geo_bypass = st.checkbox("Force Geo-Bypass (US)", value=True)

    st.divider()
    if st.button("🗑️ Reset Studio"):
        st.session_state.transcript_raw = ""
        st.session_state.transcript_tagged = ""
        st.session_state.chapter = ""
        st.session_state.processed = False
        clean_temp_files()
        st.rerun()

# ---------- INPUT TABS ----------

tab_up, tab_url, tab_live = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Notes"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov"])

with tab_url:
    url_link = st.text_input("Paste Disney+/DisneyNow/YouTube URL:")

with tab_live:
    live_notes = st.text_area("Live Production Notes:", placeholder="Add plot twists here...")

# ---------- MAIN BUTTON ----------

if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.error("Please upload a video file or provide a URL before starting production.")
    else:
        with st.status("🎬 Whisper + Gemini pipeline running...") as status:
            try:
                status.update(label="⬇️ Downloading / saving video...", state="running")
                clean_temp_files()
                source = "temp_video.mp4"

                # Download or save video
                if file_vid:
                    with open(source, "wb") as f:
                        f.write(file_vid.getbuffer())
                elif url_link:
                    ydl_cmd = ["yt-dlp", "-f", "best", "-o", source]
                    if geo_bypass:
                        ydl_cmd.extend(["--geo-bypass", "--geo-bypass-country", "US"])
                    if cookie_file:
                        with open("cookies.txt", "wb") as f:
                            f.write(cookie_file.getbuffer())
                        ydl_cmd.extend(["--cookies", "cookies.txt"])
                    ydl_cmd.append(url_link)
                    subprocess.run(ydl_cmd, check=True)

                # ---------- STAGE 1: WHISPER TRANSCRIPTION ----------
                status.update(label="🎧 Extracting audio & transcribing with Whisper...", state="running")
                audio_path = extract_audio(source)
                transcript_raw = whisper_transcribe(audio_path)

                if not transcript_raw or len(transcript_raw) < 50:
                    st.error("Transcript is empty or too short. Try a different video or check the audio.")
                    clean_temp_files()
                    st.stop()

                st.session_state.transcript_raw = transcript_raw

                # ---------- STAGE 2: GEMINI TAGS EACH LINE WITH SPEAKER ----------
                status.update(label="📝 Gemini tagging each line with speaker names...", state="running")
                model = get_gemini_model()
                safety_settings = get_safety_settings()

                speaker_prompt = f"""
You are a careful dialogue editor.

CAST (name: role):
{cast_info}

RAW TRANSCRIPT (no speaker tags, may be messy):
\"\"\"{transcript_raw}\"\"\"

TASK:
1. Rewrite the transcript as clean dialogue lines.
2. For each line of speech, clearly tag the speaker using the character names from the cast list when possible.
   - Format: "Roman: I don't know if I can do this."
   - If you're not sure, use "Unknown:" but try to infer from context.
3. Keep the wording as close to the original as possible, only fixing obvious transcription errors.
4. Preserve line breaks. Do NOT summarize. Do NOT add commentary.
"""

                speaker_response = model.generate_content(
                    contents=speaker_prompt,
                    safety_settings=safety_settings,
                )
                transcript_tagged = (speaker_response.text or "").strip() if speaker_response else ""

                if not transcript_tagged or len(transcript_tagged) < 50:
                    transcript_tagged = transcript_raw  # fallback

                st.session_state.transcript_tagged = transcript_tagged

                # ---------- STAGE 3: GEMINI WRITES YA NOVEL CHAPTER ----------
                status.update(label="📖 Gemini writing YA-style novel chapter from POV...", state="running")

                focus_characters_str = ", ".join(focus_characters) if focus_characters else "all characters"

                novel_prompt = f"""
You are a skilled YA novelist.

CAST (name: role):
{cast_info}

PRIMARY NARRATOR POV:
{pov_choice}

FOCUS CHARACTERS:
{focus_characters_str}

DIRECTOR NOTES:
{live_notes}

SOURCE TRANSCRIPT (each line tagged with speaker):
\"\"\"{transcript_tagged}\"\"\"

TASK:
Using the transcript as the backbone, write a ~2500-word YA-style novel chapter.

REQUIREMENTS:
- First-person POV from {pov_choice}.
- Show rich internal thoughts, emotions, and reactions of {pov_choice}.
- Use the speaker tags to keep who-said-what consistent with the transcript.
- Include interactions and dialogue with the other characters, especially: {focus_characters_str}.
- Keep the tone grounded, emotional, and character-driven, like a YA contemporary / young adult novel.
- Preserve the key events and emotional beats from the transcript, but you may add internal monologue, sensory detail, and subtle expansions.
- Make Giada explicitly the mother (if she appears).
- Do NOT include analysis, explanation, or meta-commentary. Output ONLY the story text.
"""

                novel_response = model.generate_content(
                    contents=novel_prompt,
                    safety_settings=safety_settings,
                )
                chapter_text = (novel_response.text or "").strip() if novel_response else ""

                if not chapter_text or len(chapter_text) < 100:
                    st.error("Gemini returned an empty or very short chapter. Try a different video or shorter content.")
                    clean_temp_files()
                    st.stop()

                st.session_state.chapter = chapter_text
                st.session_state.processed = True

                status.update(label="✅ Production complete! (Whisper + Gemini)", state="complete")
                clean_temp_files()
                st.rerun()

            except subprocess.CalledProcessError as e:
                st.error(f"Download / ffmpeg error: {e}")
                clean_temp_files()
            except Exception as e:
                st.error(f"Error: {e}")
                clean_temp_files()

# ---------- RESULTS HUB ----------

if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📜 Transcript (speaker-tagged)")
        st.text_area("T-Preview", st.session_state.transcript_tagged, height=450)
        st.download_button(
            "📥 Save Transcript (Word)",
            create_docx("Transcript", st.session_state.transcript_tagged),
            "Transcript.docx",
        )

    with col2:
        st.subheader(f"📖 Novel: {pov_choice} POV (YA-style)")
        st.text_area("N-Preview", st.session_state.chapter, height=450)
        st.download_button(
            "📥 Save Novel (Word)",
            create_docx(f"{pov_choice} Chapter", st.session_state.chapter),
            "Novel.docx",
        )

