import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# ------------------- CONFIG -------------------
st.set_page_config(page_title="POV Cloud DVR & Story Engine", layout="wide", page_icon="🎬")

if "recorded_files" not in st.session_state:
    st.session_state.recorded_files = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🔑 Missing GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

# ------------------- HELPERS -------------------
def start_dvr(url: str, pov_name: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rec_{ts}.mp4"
    log_file = f"log_{ts}.txt"

    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/mp4",
        "--no-playlist",
        "-o", filename,
        url,
    ]

    with open(log_file, "w") as f:
        subprocess.Popen(cmd, stdout=f, stderr=f)

    return filename, log_file

def compress_video(input_path: str, output_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-acodec", "aac",
        "-b:a", "128k",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

def safe_file_exists(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0

# ------------------- UI -------------------
st.title("☁️ POV Cloud DVR & Writing Engine")

tab_queue, tab_library = st.tabs(["📥 Add to Queue", "📚 Library & Results"])

# ------------------- TAB 1: QUEUE -------------------
with tab_queue:
    st.info("Queue URLs you are legally allowed to download. They will be recorded in the background.")
    video_url = st.text_input("Paste URL:")
    pov_choice = st.selectbox("Narrator POV:", ["Roman", "Billie", "Justin", "Milo", "Custom"])
    if pov_choice == "Custom":
        pov_choice = st.text_input("Custom POV name:", value="Roman")

    if st.button("🔴 Start Background Recording"):
        if not video_url:
            st.error("Please paste a URL first.")
        else:
            fn, log = start_dvr(video_url, pov_choice)
            st.session_state.recorded_files.append(
                {
                    "file": fn,
                    "log": log,
                    "pov": pov_choice,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )
            st.success(f"Queued recording: {fn}")
            st.toast("Recording started in background.")

# ------------------- TAB 2: LIBRARY -------------------
with tab_library:
    if st.button("🔄 Refresh Library"):
        st.rerun()

    if not st.session_state.recorded_files:
        st.write("No recordings yet. Add one in the 'Add to Queue' tab.")
    else:
        for idx, item in enumerate(st.session_state.recorded_files):
            file_name = item["file"]
            log_name = item["log"]

            with st.container(border=True):
                col_info, col_play, col_write = st.columns([2, 1, 1])

                with col_info:
                    st.write(f"🎥 **{file_name}**")
                    st.caption(f"POV: {item['pov']} | Added: {item['created_at']}")

                if safe_file_exists(file_name):
                    with col_play:
                        if st.button("📺 Play", key=f"play_{idx}"):
                            st.video(file_name)

                    with col_write:
                        if st.button("✍️ Write Story", key=f"write_{idx}"):
                            with st.status("AI is analyzing the footage...", expanded=True) as status:
                                try:
                                    # 1. Compress for Gemini
                                    status.write("🔧 Compressing video for Gemini compatibility...")
                                    compressed = f"compressed_{file_name}"
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
