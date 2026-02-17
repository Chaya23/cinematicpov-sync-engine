import os
import sys
import tempfile
import subprocess
import traceback
import streamlit as st

# Ensure local imports work on Streamlit Cloud
sys.path.append(os.path.dirname(__file__))

# ---- Import processor with visible errors ----
try:
    from processor import CastScriptEngine
except Exception:
    st.set_page_config(page_title="CastScript AI", layout="wide")
    st.error("❌ Failed to import processor.py")
    st.code(traceback.format_exc())
    st.stop()

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="🎬 CastScript AI",
    layout="wide",
    page_icon="🎬"
)

BLOCKED_HINTS = [
    "disneynow.com",
    "disneyplus.com",
    "netflix.com",
    "primevideo.com",
    ".m3u8",
    ".mpd",
]

def is_blocked_url(url: str) -> bool:
    return any(x in (url or "").lower() for x in BLOCKED_HINTS)

def ffmpeg_available() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except Exception:
        return False

def download_video(url: str, output_path: str):
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bv*+ba/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        url,
    ]
    subprocess.run(cmd, check=True)

# ---------------- UI ----------------
st.title("🎬 CastScript AI (Universal)")
st.caption(
    "Upload or URL → Whisper Transcript → Optional Speaker Diarization → POV Rewrite\n\n"
    "🚫 DRM streaming platforms are blocked."
)

with st.expander("ℹ️ Read this first"):
    st.markdown(
        """
        **Supported**
        - YouTube
        - Public / direct video links
        - Uploaded files you own

        **Not supported**
        - DisneyNow / Disney+ / Netflix / Prime
        - `.m3u8` / `.mpd` streams
        - DRM-protected platforms

        **Streamlit Cloud requirement**
        Your repo **must** include `packages.txt` with:
        ```
        ffmpeg
        ```
        """
    )

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    whisper_model = st.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium"],
        index=1
    )

    enable_diarization = st.checkbox(
        "Enable speaker diarization (pyannote)",
        value=False,
        help="Optional. Safe-fails on Streamlit Cloud."
    )

    st.divider()
    st.header("🎭 POV Rewrite")

    cast_info = st.text_area(
        "Cast members (Name - Role)",
        placeholder="Roman - Older brother\nBillie - Chosen One\nJustin - Father",
        height=140
    )

    pov_name = st.text_input(
        "Rewrite POV for",
        placeholder="Roman"
    )

    st.caption("POV rewrite requires GEMINI_API_KEY.")

# ---------------- INPUT ----------------
st.subheader("📥 Input")

url = st.text_input(
    "Paste URL (YouTube / public video)",
    placeholder="https://www.youtube.com/watch?v=..."
)

uploaded_file = st.file_uploader(
    "Or upload a video file",
    type=["mp4", "mkv", "mov", "webm", "m4v"]
)

run_btn = st.button("🚀 Run CastScript", use_container_width=True)

# ---------------- RUN ----------------
if run_btn:
    if not ffmpeg_available():
        st.error(
            "❌ ffmpeg not available.\n\n"
            "On Streamlit Cloud, add `packages.txt` with `ffmpeg`."
        )
        st.stop()

    if not url and not uploaded_file:
        st.error("Please provide a URL or upload a file.")
        st.stop()

    if url and is_blocked_url(url):
        st.error(
            "🚫 This URL is DRM-protected or manifest-based.\n\n"
            "Upload a file you own or use a YouTube/public link."
        )
        st.stop()

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")

        # --- Get video ---
        if uploaded_file:
            with open(video_path, "wb") as f:
                f.write(uploaded_file.read())
        else:
            with st.status("Downloading video…", expanded=True) as status:
                try:
                    download_video(url, video_path)
                    status.update(label="✅ Download complete", state="complete")
                except Exception:
                    status.update(label="❌ Download failed", state="error")
                    st.code(traceback.format_exc())
                    st.stop()

        # Preview
        try:
            st.video(video_path)
        except Exception:
            pass

        # --- Engine ---
        with st.status("Initializing engine…", expanded=True):
            engine = CastScriptEngine(
                whisper_model=whisper_model,
                enable_diarization=enable_diarization
            )

        # --- Process ---
        with st.status("🎧 Transcribing…", expanded=True):
            try:
                result = engine.process_video_or_url(video_path)
            except Exception:
                st.error("Processing failed.")
                st.code(traceback.format_exc())
                st.stop()

        st.success("✅ Done")

        # ---------------- OUTPUT ----------------
        tab1, tab2, tab3 = st.tabs(
            ["📜 Transcript", "🗣 Diarization", "✍️ POV Rewrite"]
        )

        with tab1:
            st.text_area(
                "Transcript",
                result.transcript_text,
                height=420
            )
            st.download_button(
                "⬇️ Download transcript.txt",
                result.transcript_text,
                file_name="transcript.txt"
            )

        with tab2:
            if getattr(result, "diarization_error", None):
                st.warning(result.diarization_error)

            if result.diarization is None:
                st.info("No diarization available.")
            else:
                st.write(result.diarization)

        with tab3:
            if not pov_name or not cast_info:
                st.info("Add cast info and POV name in the sidebar.")
            else:
                with st.status("Writing POV…", expanded=True):
                    pov_text = engine.rewrite_pov(
                        transcript=result.transcript_text,
                        character_name=pov_name,
                        cast_info=cast_info
                    )

                st.text_area(
                    f"POV: {pov_name}",
                    pov_text,
                    height=420
                )
                st.download_button(
                    "⬇️ Download pov.txt",
                    pov_text,
                    file_name=f"pov_{pov_name}.txt"
                )

st.divider()
st.caption("Only process content you own or have permission to use.")
