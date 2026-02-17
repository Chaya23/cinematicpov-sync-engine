  import streamlit as st
import os
import subprocess
import tempfile
from processor import CastScriptEngine

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="🎬 CastScript AI",
    layout="wide",
    page_icon="🎬"
)

BLOCKED_SITES = [
    "disneynow.com",
    "disneyplus.com",
    "netflix.com",
    "primevideo.com",
    ".m3u8",
    ".mpd"
]

# ---------------- HELPERS ----------------
def is_supported_url(url: str) -> bool:
    return not any(b in url.lower() for b in BLOCKED_SITES)

def download_with_ytdlp(url: str, out_path: str):
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", out_path,
        url
    ]
    subprocess.run(cmd, check=True)

# ---------------- UI ----------------
st.title("🎬 CastScript AI (Universal)")
st.caption(
    "Upload or YouTube → Whisper Transcript → Optional Speaker Diarization → POV Rewrite\n\n"
    "🚫 DRM streaming platforms are blocked."
)

# -------- SETTINGS --------
with st.sidebar:
    st.header("⚙️ Settings")
    whisper_model = st.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium"],
        index=1
    )
    enable_diarization = st.checkbox("Enable speaker diarization", value=True)

    st.divider()
    st.header("🎭 Cast Members")
    cast_input = st.text_area(
        "Name - Role (one per line)",
        placeholder="Roman - Older brother\nBillie - Chosen one\nJustin - Father"
    )
    target_pov = st.text_input("Rewrite POV for:", placeholder="Roman")

# -------- INPUT --------
st.subheader("📥 Input")

url_input = st.text_input(
    "Paste URL (YouTube or direct MP4)",
    placeholder="https://youtube.com/watch?v=..."
)

uploaded_file = st.file_uploader(
    "Or upload a video file",
    type=["mp4", "mkv", "mov", "webm", "m4v"]
)

run_btn = st.button("🚀 Run CastScript")

# ---------------- PROCESS ----------------
if run_btn:
    if not url_input and not uploaded_file:
        st.error("Please provide a URL or upload a video.")
        st.stop()

    if url_input and not is_supported_url(url_input):
        st.error(
            "🚫 This URL is DRM-protected and cannot be processed.\n\n"
            "Please upload a video file or use YouTube/public links."
        )
        st.stop()

    with st.status("Preparing engine...", expanded=True) as status:
        engine = CastScriptEngine(
            whisper_model=whisper_model,
            enable_diarization=enable_diarization
        )
        status.update(label="Engine ready", state="complete")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")

        if uploaded_file:
            with open(video_path, "wb") as f:
                f.write(uploaded_file.read())
        else:
            with st.status("Downloading video...", expanded=True):
                download_with_ytdlp(url_input, video_path)

        # -------- TRANSCRIBE --------
        with st.status("🎧 Transcribing audio...", expanded=True):
            result = engine.process_video_or_url(video_path)

        # -------- OUTPUT --------
        st.success("Transcription complete!")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📜 Transcript")
            st.text_area(
                "Transcript",
                result.transcript_text,
                height=400
            )

        with col2:
            if target_pov and cast_input:
                with st.status("✍️ Writing POV chapter...", expanded=True):
                    pov_text = engine.rewrite_pov(
                        transcript=result.transcript_text,
                        character_name=target_pov,
                        cast_info=cast_input
                    )
                st.subheader(f"📖 POV Chapter — {target_pov}")
                st.text_area(
                    "POV Rewrite",
                    pov_text,
                    height=400
                )
            else:
                st.info("Add cast info and POV name to enable rewrite.")

        # -------- DIARIZATION --------
        if result.diarization:
            st.subheader("🗣 Speaker Diarization")
            st.write(result.diarization)

st.divider()
st.caption(
    "⚠️ Legal note: Only upload or process content you own, have permission for, "
    "or that is public domain."
)                                  compressed = f"compressed_{file_name}"
                                    compress_video(file_name, compressed)

                                    if not safe_file_exists(compressed):
                                        status.update(label="❌ Compression failed", state="error")
                                        st.error("Compressed file not found. Check ffmpeg.")
                                        continue

                                    # 2. Upload to Gemini
                                    status.write("📤 Uploading to Gemini...")
                                    try:
                                        video_file = genai.upload_file(compressed)
                                    except Exception as e:
                                        status.update(label="❌ Upload failed", state="error")
                                        st.error(f"Gemini upload error: {e}")
                                        continue

                                    # 3. Wait for processing
                                    for _ in range(20):
                                        video_file = genai.get_file(video_file.name)
                                        state = getattr(video_file, "state", None)
                                        if state and state.name == "ACTIVE":
                                            break
                                        if state and state.name == "FAILED":
                                            status.update(label="❌ Gemini rejected the file", state="error")
                                            st.error("Gemini could not process this video.")
                                            continue
                                        time.sleep(2)

                                    if not getattr(video_file, "state", None) or video_file.state.name != "ACTIVE":
                                        status.update(label="❌ Timeout waiting for Gemini", state="error")
                                        st.error("Gemini took too long to process the file.")
                                        continue

                                    # 4. Generate transcript + chapter
                                    status.write("🧠 Generating transcript and POV chapter...")
                                    model = genai.GenerativeModel("gemini-1.5-pro")

                                    prompt = (
                                        f"You are a writer watching this video.\n"
                                        f"POV character: {item['pov']}.\n\n"
                                        "1. First, produce a full dialogue transcript.\n"
                                        "2. Then, write a YA-style first-person novel chapter from that POV.\n"
                                        "Separate the transcript and chapter with a line containing only:\n"
                                        "---SPLIT---"
                                    )

                                    response = model.generate_content([video_file, prompt])
                                    text = (response.text or "").strip()
                                    parts = text.split("---SPLIT---")

                                    transcript = parts[0].strip() if len(parts) > 0 else ""
                                    chapter = parts[1].strip() if len(parts) > 1 else ""

                                    st.session_state[f"res_{idx}"] = {
                                        "transcript": transcript,
                                        "chapter": chapter,
                                    }

                                    status.update(label="✅ Finished!", state="complete")

                                except Exception as e:
                                    status.update(label="❌ Error", state="error")
                                    st.error(f"Error during AI processing: {e}")

                    # Show results if present
                    if f"res_{idx}" in st.session_state:
                        res = st.session_state[f"res_{idx}"]
                        st.divider()
                        r1, r2 = st.columns(2)
                        with r1:
                            st.subheader("📜 Transcript")
                            st.text_area("Transcript", res["transcript"], height=300, key=f"t_{idx}")
                        with r2:
                            st.subheader(f"📖 {item['pov']}'s Chapter")
                            st.text_area("Novel", res["chapter"], height=300, key=f"n_{idx}")

                else:
                    st.warning("⏳ Still downloading or file not ready yet.")
                    if os.path.exists(log_name):
                        with st.expander("View download log"):
                            with open(log_name, "r") as f:
                                st.code(f.read()[-800:], language="text")
