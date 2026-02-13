import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="CinematicPOV Masterpiece 12.3", layout="wide", page_icon="🎬")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. QUOTA-SAFE RETRY WRAPPER ---
def safe_generate(model, content, max_retries=5):
    """Handles 429 errors with exponential backoff and jitter."""
    for attempt in range(max_retries):
        try:
            # We use a lower temperature for consistent transcripts
            return model.generate_content(content, generation_config={"temperature": 0.4})
        except exceptions.ResourceExhausted:
            wait = (2 ** attempt) + random.uniform(0, 1)
            st.warning(f"⚠️ Quota exceeded. Retrying in {wait:.1f}s... ({attempt+1}/{max_retries})")
            time.sleep(wait)
        except Exception as e:
            raise e
    raise Exception("❌ Quota fully exhausted. Please wait 1-2 minutes and try again.")

# --- 3. VIDEO DOWNLOADER (Optimized for Quota) ---
def download_optimized_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    # 480p is the 'sweet spot' for Gemini Vision: clear enough for faces, low token cost.
    ydl_opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best', 
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 4. MAIN INTERFACE ---
st.title("🎬 CinematicPOV: Author Edition v12.3")
st.caption("Optimized for 2026 Free Tier Quotas.")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Episode URL (YouTube/Disney/Solar):")
    uploaded = st.file_uploader("OR Upload Video:", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("POV Character:", chars)
    style = st.selectbox("Writing Style:", [
        "YA Fantasy (Sarah J. Maas style)", 
        "Snarky Middle Grade (Rick Riordan style)", 
        "Gothic Drama"
    ])

if st.button("🚀 GENERATE MANUSCRIPT & SCRIPT", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step 1: Video Prep
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading optimized 480p video...")
                video_path = download_optimized_video(url_input, tmp_dir)

            # Step 2: Google Files API Upload
            st.info("☁️ Uploading to Gemini Vision...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = genai.get_file(video_file.name)

            # Step 3: Analysis Phase
            st.info(f"✍️ Authoring full chapter for {pov_char}...")
            
            # Use 2.5 Flash for best free-tier reliability in 2026
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                tools=[{'google_search_retrieval': {}}] # Search grounding for episode accuracy
            )
            
            prompt = f"""
            Identify every character in this video. 
            TRANSCRIPT: Extract EVERY line of dialogue perfectly.
            STORY: Write a LONG first-person chapter from {pov_char}'s POV. 
            
            STYLE: {style}
            GROUNDING: Roman loves Lacey (the vase). Billie's Staten Island look.
            
            FORMAT:
            ---TRANSCRIPT_START---
            [Labeled Script]
            ---POV_START---
            [Novel Chapter]
            """

            response = safe_generate(model, [video_file, prompt])
            output = response.text
            
            if "---POV_START---" in output:
                parts = output.split("---POV_START---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT_START---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Success!")
            else:
                st.write(output)

            # Cleanup
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. TABS FOR RESULTS ---
if "novel" in st.session_state:
    t1, t2 = st.tabs(["📖 The Manuscript", "📝 Full Transcript"])
    with t1:
        st.markdown(f"### {pov_char}'s POV Chapter")
        st.write(st.session_state.novel)
        st.download_button("Save Chapter", st.session_state.novel, "chapter.txt")
    with t2:
        st.text_area("Dialogue Script:", st.session_state.transcript, height=500)
        st.download_button("Save Script", st.session_state.transcript, "script.txt")
