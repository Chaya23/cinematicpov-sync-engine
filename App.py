import os
import sys
import traceback
import tempfile
import subprocess

import streamlit as st

# Make sure local imports work on Streamlit Cloud
sys.path.append(os.path.dirname(__file__))

# Import engine with visible errors (no redacted crash)
try:
    from processor import CastScriptEngine
except Exception:
    st.set_page_config(page_title="CastScript AI", layout="wide")
    st.error("❌ Import failed: processor.py could not be loaded.")
    st.code(traceback.format_exc())
    st.stop()


# ------------------- CONFIG -------------------
st.set_page_config(page_title="🎬 CastScript AI", layout="wide", page_icon="🎬")

BLOCKED_HINTS = [
    "disneynow.com",
    "disneyplus.com",
    "netflix.com",
    "primevideo.com",
    ".m3u8",
    ".mpd",
]

SUPPORTED_NOTE = (
    "✅ Works best with: **YouTube** and **direct downloadable video links**.\n\n"
    "🚫 Many streaming services (DisneyNow/Disney+/Netflix etc.) are DRM/manifest based "
    "and cannot be downloaded by normal tools."
)


def looks_blocked(url: str) -> bool:
    u = (url or "").lower().strip()
    return any(x in u for x in BLOCKED_HINTS)


def have_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False


def download_with_ytdlp(url: str, out_path: str):
    """
    Downloads URL to out_path using yt-dlp.
    Works for YouTube and some public sites. Not DRM services.
    """
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bv*+ba/best",
        "--merge-output-format", "mp4",
        "-o", out_path,
        url,
    ]
    subprocess.run(cmd, check=True)


# ------------------- UI -------------------
st.title("🎬 CastScript AI (Universal)")
st.caption("URL / Upload → ffmpeg audio → Whisper transcript (+ optional diarization + POV rewrite)")

with st.expander("Read this first (important)"):
    st.markdown(SUPPORTED_NOTE)
    st.markdown(
        "**Streamlit Cloud requirement:** you must have a `packages.txt` file in GitHub containing:\n\n"
        "```txt\nffmpeg\n```"
    )

# ------------------- SIDEBAR SETTINGS -------------------
with st.sidebar:
    st.header("⚙️ Settings")

    whisper_model = st.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium"],
        index=1,
        help="Bigger = better accuracy but slower."
    )

    enable_diarization = st.checkbox(
        "Enable speaker diarization (pyannote)",
        value=False,
        help="This may fail on Streamlit Cloud depending on build + gated model access."
    )

    st.divider()
    st.header("🎭 POV Rewrite")

    cast_input = st.text_area(
        "Cast members (Name - Role, one per line)",
        placeholder="Roman - Older brother\nBillie - Chosen One\nJustin - Father",
        height=140
    )

    pov_name = st.text_input(
        "Rewrite POV for (character name)",
        placeholder="Roman"
    )

    st.caption("POV rewrite requires `GEMINI_API_KEY` set in Streamlit Secrets or .env.")

# ------------------- INPUT AREA -------------------
st.subheader("📥 Input")

url = st.text_input(
    "Paste URL (YouTube / public video link)",
    placeholder="https://www.youtube.com/watch?v=..."
)

uploaded = st.file_uploader(
    "Or upload a video file",
    type=["mp4", "mkv", "mov", "webm", "m4v"]
)

colA, colB = st.columns([1, 1])

with colA:
    run_btn = st.button("🚀 Run transcription", use_container_width=True)

with colB:
    st.write("")
    st.write("")
    st.write(f"ffmpeg detected: {'✅' if have_ffmpeg() else '❌'}")

if run_btn:
    if not have_ffmpeg():
        st.error(
            "❌ ffmpeg is not available.\n\n"
            "If you are on Streamlit Cloud, add `packages.txt` with `ffmpeg`."
        )
        st.stop()

    if not url and not uploaded:
        st.error("Please paste a URL or upload a file.")
        st.stop()

    if url and looks_blocked(url):
        st.error(
            "🚫 This looks like a DRM/manifest streaming page (.m3u8/.mpd / DisneyNow/Netflix etc.).\n\n"
            "Upload a file you own or use a YouTube/public link."
        )
        st.stop()

    # --- Prepare workspace ---
    with tempfile.TemporaryDirectory() as tmpdir:
        local_video = os.path.join(tmpdir, "input.mp4")

        # --- Get the video ---
        if uploaded:
            with st.status("Saving uploaded file...", expanded=False) as status:
                with open(local_video, "wb") as f:
                    f.write(uploaded.read())
                status.update(label="✅ Upload saved", state="complete")
        else:
            with st.status("Downloading with yt-dlp...", expanded=True) as status:
                try:
                    download_with_ytdlp(url, local_video)
                    status.update(label="✅ Download complete", state="complete")
                except Exception:
                    status.update(label="❌ Download failed", state="error")
                    st.error("yt-dlp failed to download this URL (likely DRM/blocked or not supported).")
                    st.code(traceback.format_exc())
                    st.stop()

        # Preview if possible
        try:
            st.video(local_video)
        except Exception:
            pass

        # --- Run engine ---
        with st.status("Initializing engine...", expanded=True) as status:
            try:
                engine = CastScriptEngine(
                    whisper_model=whisper_model,
                    enable_diarization=enable_diarization
                )
                status.update(label="✅ Engine ready", state="complete")
            except Exception:
                status.update(label="❌ Engine init failed", state="error")
                st.code(traceback.format_exc())
                st.stop()

        with st.status("🎧 Transcribing (Whisper)...", expanded=True) as status:
            try:
                result = engine.process_video_or_url(local_video)
                status.update(label="✅ Transcription complete", state="complete")
            except Exception:
                status.update(label="❌ Processing failed", state="error")
                st.code(traceback.format_exc())
                st.stop()

        # ---------------- OUTPUTS ----------------
        st.success("Done ✅")

        tab1, tab2, tab3 = st.tabs(["📜 Transcript", "🗣 Diarization", "✍️ POV Rewrite"])

        with tab1:
            st.subheader("Transcript")
            st.text_area("Transcript", result.transcript_text, height=420)

            st.download_button(
                "⬇️ Download transcript.txt",
                data=result.transcript_text.encode("utf-8"),
                file_name="transcript.txt",
                mime="text/plain"
            )

        with tab2:
            st.subheader("Speaker diarization")
            if getattr(result, "diarization_error", None):
                st.warning(result.diarization_error)

            if result.diarization is None:
                st.info("No diarization available (disabled or failed).")
            else:
                st.write(result.diarization)

        with tab3:
            st.subheader("POV Rewrite")
            if not cast_input or not pov_name:
                st.info("Add cast info + POV name in the sidebar to enable rewrite.")
            else:
                with st.status("Writing POV chapter...", expanded=True) as status:
                    try:
                        pov_text = engine.rewrite_pov(
                            transcript=result.transcript_text,
                            character_name=pov_name,
                            cast_info=cast_input
                        )
                        status.update(label="✅ POV complete", state="complete")
                    except Exception:
                        status.update(label="❌ POV failed", state="error")
                        st.code(traceback.format_exc())
                        st.stop()

                st.text_area(f"POV: {pov_name}", pov_text, height=420)

                st.download_button(
                    "⬇️ Download pov.txt",
                    data=pov_text.encode("utf-8"),
                    file_name=f"pov_{pov_name}.txt",
                    mime="text/plain"
                )

st.divider()
st.caption("Only use content you own or have rights to process.")
