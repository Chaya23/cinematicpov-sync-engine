import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import subprocess
from docx import Document
from io import BytesIO
import os

# 1. STUDIO CONFIG
st.set_page_config(page_title="Roman's Master Studio", layout="wide")

# API KEY SETUP
api_key = st.secrets.get("GEMINI_API_KEY", "")
api_key = api_key.strip() if api_key else ""
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 API Key missing from Secrets.")
    st.stop()

# PERSISTENCE
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "chapter" not in st.session_state:
    st.session_state.chapter = ""
if "processed" not in st.session_state:
    st.session_state.processed = False

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
    for f in ["temp_video.mp4"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

# 2. SIDEBAR: PRODUCTION BIBLE & SETTINGS
with st.sidebar:
    st.header("🎭 Character Bible")
    cast_info = st.text_area(
        "Cast Roles (Editable):",
        "Giada: Mother\nJustin: Father\nRoman: Protagonist\nTheresa: Grandmother"
    )

    # Parse cast names from the cast_info
    cast_lines = [line.strip() for line in cast_info.splitlines() if line.strip()]
    cast_names = []
    for line in cast_lines:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name:
                cast_names.append(name)

    st.header("👤 POV & Focus Characters")
    pov_options = ["Custom"]
    pov_options.extend(cast_names)
    pov_choice = st.selectbox("Primary Narrator POV:", pov_options)

    if pov_choice == "Custom":
        pov_choice = st.text_input("Enter Custom Narrator Name:", value="Roman Russo")

    focus_characters = st.multiselect(
        "Focus Characters (multi-select):",
        options=cast_names,
        default=cast_names
    )

    st.header("🌐 Bypass Tools")
    cookie_file = st.file_uploader("Upload cookies.txt (For Disney/Region bypass)", type=["txt"])
    geo_bypass = st.checkbox("Force Geo-Bypass (US)", value=True)

    st.divider()
    if st.button("🗑️ Reset Studio"):
        st.session_state.transcript = ""
        st.session_state.chapter = ""
        st.session_state.processed = False
        clean_temp_files()
        st.rerun()

# 3. TABS: INPUT METHODS
tab_up, tab_url, tab_live = st.tabs(["📁 File Upload", "🌐 URL Sync", "🎙️ Live Notes"])

with tab_up:
    file_vid = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov"])

with tab_url:
    url_link = st.text_input("Paste DisneyNow/YouTube URL:")

with tab_live:
    live_notes = st.text_area("Live Production Notes:", placeholder="Add plot twists here...")

# 4. PRODUCTION ENGINE
if st.button("🚀 START PRODUCTION", use_container_width=True):
    if not file_vid and not url_link:
        st.error("Please upload a video file or provide a URL before starting production.")
    else:
        with st.status("🎬 Cloud Processing & Novel Generation...") as status:
            try:
                status.update(label="🔍 Resolving Gemini model...", state="running")
                # DYNAMIC MODEL RESOLVER
                available_models = [
                    m.name
                    for m in genai.list_models()
                    if hasattr(m, "supported_generation_methods")
                    and "generateContent" in m.supported_generation_methods
                ]
                flash_models = [m for m in available_models if "flash" in m.lower()]
                selected_model = flash_models[0] if flash_models else "models/gemini-1.5-flash"
                model = genai.GenerativeModel(selected_model)
                safety_settings = get_safety_settings()

                # STORAGE CLEANUP (Gemini file store)
                try:
                    for f in genai.list_files():
                        genai.delete_file(f.name)
                except Exception:
                    pass

                source = "temp_video.mp4"
                clean_temp_files()

                status.update(label="⬇️ Downloading / saving video (yt-dlp/local)...", state="running")
                # --- DOWNLOAD / SAVE VIDEO ---
                if file_vid:
                    with open(source, "wb") as f:
                        f.write(file_vid.getbuffer())
                elif url_link:
                    ydl_cmd = ["yt-dlp", "-f", "best[ext=mp4]", "-o", source]
                    if geo_bypass:
                        ydl_cmd.extend(["--geo-bypass", "--geo-bypass-country", "US"])
                    if cookie_file:
                        with open("cookies.txt", "wb") as f:
                            f.write(cookie_file.getbuffer())
                        ydl_cmd.extend(["--cookies", "cookies.txt"])
                    ydl_cmd.append(url_link)
                    subprocess.run(ydl_cmd, check=True)

                status.update(label="📤 Uploading video to Gemini (cloud watch)...", state="running")
                genai_file = genai.upload_file(path=source)

                # Wait for file processing in cloud
                while getattr(genai_file, "state", None) and genai_file.state.name == "PROCESSING":
                    time.sleep(5)
                    genai_file = genai.get_file(genai_file.name)

                if not hasattr(genai_file, "uri"):
                    st.error("Gemini did not return a valid file URI. Video may be unsupported or blocked.")
                    clean_temp_files()
                    st.stop()

                file_uri = genai_file.uri

                # ---------- STAGE 1: CLOUD TRANSCRIPT WITH SPEAKERS ----------
                status.update(label="📝 Gemini watching video & transcribing (who said what)...", state="running")

                transcript_prompt = f"""
You are given a video file hosted in the cloud.

<VIDEO_FILE_URI>
{file_uri}
</VIDEO_FILE_URI>

CAST (name: role):
{cast_info}

TASK:
1. Watch/listen to the entire video.
2. Produce a detailed transcript of the dialogue and important on-screen text.
3. For each line of dialogue, clearly tag who is speaking using the character names from the cast list when possible.
   - Format like: "Roman: I don't know if I can do this."
   - If you're not sure, use "Unknown:" but try to infer from context.
4. Keep line breaks natural. Do NOT summarize. Do NOT add commentary.
"""

                transcript_response = model.generate_content(
                    contents=transcript_prompt,
                    safety_settings=safety_settings,
                )

                transcript_text = (transcript_response.text or "").strip() if transcript_response else ""

                if not transcript_text or len(transcript_text) < 50:
                    st.error(
                        "Gemini returned an empty or very short transcript. "
                        "If this is a streaming/DRM video, it may be blocked."
                    )
                    clean_temp_files()
                    st.stop()

                st.session_state.transcript = transcript_text

                # ---------- STAGE 2: YA NOVEL CHAPTER ----------
                status.update(label="📖 Generating YA-style novel chapter from transcript...", state="running")

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

SOURCE TRANSCRIPT (with speaker tags):
\"\"\"{transcript_text}\"\"\"

TASK:
Using the transcript as the backbone, write a ~2500-word YA-style novel chapter.

REQUIREMENTS:
- First-person POV from {pov_choice}.
- Show rich internal thoughts, emotions, and reactions of {pov_choice}.
- Use the speaker tags to keep who-said-what consistent with the transcript.
- Include interactions and dialogue with the other characters, especially: {focus_characters_str}.
- Keep the tone grounded, emotional, and character-driven, like a YA contemporary or YA drama.
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

                status.update(label="✅ Cloud production complete!", state="complete")
                clean_temp_files()
                st.rerun()

            except subprocess.CalledProcessError as e:
                st.error(f"Download error (yt-dlp / ffmpeg): {e}")
                clean_temp_files()
            except Exception as e:
                st.error(f"Error: {e}")
                clean_temp_files()

# 5. RESULTS HUB
if st.session_state.processed:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📜 Transcript (with speakers)")
        st.text_area("T-Preview", st.session_state.transcript, height=450)
        st.download_button(
            "📥 Save Transcript (Word)",
            create_docx("Transcript", st.session_state.transcript),
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
