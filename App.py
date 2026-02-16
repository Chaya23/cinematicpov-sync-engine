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

st.set_page_config(page_title="Cinematic POV Story Engine (Audio Only)", layout="wide")

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
    for f in ["temp_audio_source", "temp_audio.mp3", "cookies.txt"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def extract_audio(input_path: str, audio_path: str = "temp_audio.mp3") -> str:
    """Takes any media file (audio or video) and converts it to MP3."""
    if os.path.exists(audio_path):
        os.remove(audio_path)
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "mp3", audio_path]
    subprocess.run(cmd, check=True)
    return audio_path


def whisper_transcribe(audio_path: str) -> str:
    # High accuracy: use Whisper large
    model = whisper.load_model("large")
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
        while getattr(file_obj, "state", None) and file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        if getattr(file_obj, "state", None) and file_obj.state.name == "FAILED":
            return None
        return file_obj
    except Exception:
        return None


def download_audio_only(url: str, cookie_file) -> str:
    """Uses yt-dlp to download audio-only stream from a URL."""
    out_path = "temp_audio_source"
    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = ["yt-dlp", "-f", "bestaudio", "-o", out_path]
    if cookie_file:
        with open("cookies.txt", "wb") as f:
            f.write(cookie_file.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])
    cmd.append(url)
    subprocess.run(cmd, check=True)
    return out_path


# ---------------- SIDEBAR (CHARACTERS + POV) ----------------

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
        for key in ["transcript_raw", "plot_summary", "transcript_tagged", "chapter", "processed"]:
            st.session_state[key] = "" if key != "processed" else False
        clean_temp_files()
        st.rerun()


# ---------------- MAIN UI ----------------

st.title("🎬 Cinematic POV Story Engine – Audio Only")

st.markdown(
    """
This app turns real audio from shows or movies into a **YA-style POV novel chapter** using your own cast list.

### 🔧 What it does

1. You give it **audio** from a show or movie:
   - **Tab 1 – URL:** paste a streaming URL (DisneyNow, Disney+, YouTube, etc.) – it downloads **audio only**  
   - **Tab 2 – File upload:** upload a PlayOn recording, screen recording, or any audio/video file  

2. It converts everything to MP3 and uses **Whisper (large)** to transcribe the audio as accurately as possible.

3. **Gemini** then:
   - Listens to the audio  
   - Reads the transcript  
   - Creates a detailed **plot summary**  
   - Uses your **cast list** to tag **who said what**  
   - Writes a **YA-style novel chapter** from your chosen POV.

4. You can download:
   - The **speaker-tagged transcript** (Word)  
   - The **novel chapter** (Word)
"""
)

with st.expander("📖 How to use this app (step by step)"):
    st.markdown(
        """
### 1️⃣ Set up your characters and POV (left sidebar)
- Edit the **Character list** so it matches your show (e.g. `Giada: Mother`, `Roman: Protagonist`).
- Choose a **POV narrator** (or type a custom name).
- Pick which characters to **focus on** in the chapter.

### 2️⃣ Choose how to give the app your audio

**Option A – URL (Tab: “URL – audio only”)**
- Paste a streaming URL (DisneyNow, Disney+, YouTube, etc.).
- For **DisneyNow**, you **must** upload a `cookies.txt` file in the sidebar (see instructions below).

**Option B – File upload (Tab: “File upload / live recording”)**
- Upload a file from:
  - PlayOn recordings  
  - Screen recordings (phone or computer)  
  - Voice memos / audio recordings  
  - Any MP4, MOV, MKV, MP3, WAV, M4A, AAC  

### 3️⃣ (Optional) Add writer notes
- In the **Writer notes** tab, you can describe:
  - Tone (soft, intense, funny, dark, etc.)
  - Themes (family, grief, romance, etc.)
  - What to emphasise in the chapter.

### 4️⃣ Run the pipeline
- Click **“🚀 Run full audio pipeline”**.
- The app will:
  1. Download or read the audio  
  2. Convert to MP3  
  3. Transcribe with Whisper (large)  
  4. Generate a plot summary  
  5. Tag who said what  
  6. Write a YA-style POV chapter  

### 5️⃣ Read and download results
- Scroll down to see:
  - **Plot summary**
  - **Speaker-tagged transcript**
  - **POV novel chapter**
- Use the **Download** buttons to save Word files.

### 🔁 If something fails
- If you see a **yt-dlp** or **ffmpeg** error:
  - For DisneyNow/Disney+, check `cookies.txt` or use **File upload** instead.
- If the transcript is very short, try a different file or shorter clip.
"""
    )

with st.expander("ℹ️ How to get cookies.txt for DisneyNow (required for URL mode)"):
    st.markdown(
        """
DisneyNow uses short‑lived security tokens. To download audio from DisneyNow URLs, you **must** provide a `cookies.txt` file from your own device.  
This file contains your **login session**, **region**, and **access tokens** so yt‑dlp can request a fresh playlist every time.

### 📱 iPhone (Safari)
1. Install the extension **“Get cookies.txt”** from the App Store.
2. Open **Settings → Safari → Extensions** and enable it.
3. Open Safari and go to **disneynow.com**.
4. Log in and open the episode you want.
5. Tap the **AA** icon → **Get cookies.txt** → **Export** → **Save to Files**.
6. Upload the saved `cookies.txt` file in the sidebar.

### 🤖 Android (Chrome or Kiwi Browser)
1. Install the extension **“Get cookies.txt”** from the Chrome Web Store.
2. Open **disneynow.com** and log in.
3. Open the browser menu → **Extensions** → **Get cookies.txt**.
4. Tap **Export** and save the file.
5. Upload `cookies.txt` in the sidebar.

### 🖥️ Windows / Mac (Chrome, Edge, Firefox)
1. Install the extension **“Get cookies.txt”**.
2. Go to **disneynow.com** and log in.
3. Click the extension → **Export cookies for this site**.
4. Save the file as `cookies.txt`.
5. Upload it in the sidebar.

### ❗ Important notes
- The cookies file must come from **your own logged‑in device**.
- Cookies expire — if downloads stop working, export a **fresh** `cookies.txt`.
- If DisneyNow still fails, use the **File upload** tab instead (PlayOn recordings or screen recordings always work).
"""
    )

tab_url, tab_file, tab_notes = st.tabs(
    ["🌐 URL (audio only)", "📁 File upload / live recording", "📝 Writer notes"]
)

with tab_url:
    url_link = st.text_input("Paste video/audio URL (DisneyNow, Disney+, YouTube, etc.):")

with tab_file:
    file_media = st.file_uploader(
        "Upload audio or video (PlayOn MP4, screen recording, MP3, WAV, etc.)",
        type=["mp4", "mov", "mkv", "mp3", "wav", "m4a", "aac"],
    )

with tab_notes:
    live_notes = st.text_area(
        "Director / writer notes (optional):",
        placeholder="Tone, themes, what to emphasise in the chapter...",
        height=150,
    )


# ---------------- PIPELINE BUTTON ----------------

if st.button("🚀 Run full audio pipeline", use_container_width=True):
    if not file_media and not url_link:
        st.error("Please upload a file or provide a URL.")
    else:
        with st.status("Running audio → Whisper → Gemini pipeline...", expanded=True) as status:
            try:
                clean_temp_files()

                # 1. Get audio source (URL or file)
                status.update(label="⬇️ Getting audio source...", state="running")

                if url_link:
                    # DisneyNow requires cookies.txt
                    if "disneynow.com" in url_link.lower() and not cookie_file:
                        st.error("DisneyNow URLs require cookies.txt. Please upload your cookies file in the sidebar.")
                        clean_temp_files()
                        st.stop()
                    try:
                        source_audio = download_audio_only(url_link, cookie_file)
                    except subprocess.CalledProcessError as e:
                        st.error(
                            f"yt-dlp audio download failed.\n\n"
                            f"Details: {e}\n\n"
                            "If this is a DisneyNow/Disney+ link, make sure cookies.txt is valid, "
                            "or instead upload a PlayOn/screen recording file in the File upload tab."
                        )
                        clean_temp_files()
                        st.stop()
                else:
                    # Save uploaded file as temp_audio_source
                    source_audio = "temp_audio_source"
                    with open(source_audio, "wb") as f:
                        f.write(file_media.getbuffer())

                # 2. Convert to MP3 (ffmpeg)
                status.update(label="🎧 Converting to MP3 with ffmpeg...", state="running")
                audio_path = extract_audio(source_audio, "temp_audio.mp3")

                # 3. Whisper transcription
                status.update(label="📝 Transcribing audio with Whisper (large)...", state="running")
                transcript_raw = whisper_transcribe(audio_path)
                if not transcript_raw or len(transcript_raw) < 50:
                    st.error("Transcript is empty or too short. Check the audio or try another file/URL.")
                    clean_temp_files()
                    st.stop()
                st.session_state.transcript_raw = transcript_raw

                # 4. Gemini model
                model = get_gemini_model()
                safety = get_safety_settings()

                # 5. Upload audio to Gemini (so it can LISTEN)
                status.update(label="📤 Uploading audio to Gemini...", state="running")
                audio_file_obj = upload_audio_to_gemini(audio_path)

                # 6. Plot summary (Gemini listens + reads)
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
1. Listen carefully to the audio and read the transcript.
2. Produce a clear plot summary of what happens in this audio.
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
1. Produce a clear plot summary of what happens in this audio.
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
                    st.error("Gemini returned an empty or very short chapter. Try a different audio or shorter content.")
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
