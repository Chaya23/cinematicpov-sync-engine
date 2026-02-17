import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# --- 1. SYSTEM CONFIG ---
st.set_page_config(page_title="POV DVR: Universal Studio", layout="wide")

# Gemini 3 Flash (The 2026 Workhorse for Video)
MODEL_NAME = "gemini-3-flash" 

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. THE DYNAMIC CAST EDITOR ---
st.sidebar.header("📺 Show Production Settings")
show_title = st.sidebar.text_input("Show Title:", "Wizards Beyond Waverly Place")

# The magic part: Type names here to update the dropdown below
cast_raw = st.sidebar.text_area(
    "Edit Cast (Comma separated):", 
    "Roman, Billie, Justin, Milo, Winter"
)
# Convert text list to a real Python list for the dropdown
cast_list = [name.strip() for name in cast_raw.split(",") if name.strip()]

# Now the POV selector is dynamic!
pov_hero = st.sidebar.selectbox("Select Narrator POV:", cast_list)

st.sidebar.divider()
st.sidebar.caption("Cookie Support: Upload a cookies.txt from your browser to record Netflix/Disney+.")
c_file = st.sidebar.file_uploader("🍪 Upload cookies.txt", type="txt")

# --- 3. DVR DOWNLOADER ---
def dvr_download(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"show_{ts}.mp4"
    
    # Mobile-safe H264 + AAC
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    if cookies:
        with open("c.txt", "wb") as f: f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "c.txt"])

    with st.status(f"🎬 Recording {show_title}..."):
        p = subprocess.run(cmd, capture_output=True, text=True)
        return fn if p.returncode == 0 else None

# --- 4. MAIN INTERFACE ---
st.title(f"🎬 {show_title} Production Studio")

u_input = st.text_input(f"Paste Link for {show_title}:")

if st.button("🚀 Record & Analyze"):
    if not u_input:
        st.warning("Paste a link first!")
    else:
        video_path = dvr_download(u_input, c_file)
        if video_path:
            st.session_state.library.append({"file": video_path, "pov": pov_hero, "show": show_title, "cast": cast_raw})
            st.rerun()

# --- 5. THE PRODUCTION LIBRARY ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['show']}** | POV: **{item['pov']}**")
        
        if st.button(f"✨ Generate Full Production (Gemini 3)", key=f"ai_{idx}"):
            with st.status("🧠 AI is analyzing the full 24-minute episode..."):
                # Upload to Google
                gf = genai.upload_file(item['file'])
                while gf.state.name == "PROCESSING":
                    time.sleep(3)
                    gf = genai.get_file(gf.name)
                
                # Specialized prompt for LONG videos
                model = genai.GenerativeModel(MODEL_NAME)
                prompt = f"""
                VIDEO: A full episode of {item['show']}.
                CAST LIST: {item['cast']}
                
                Your output must be very long. Do not cut off the transcript.
                
                PART 1: VERBATIM TRANSCRIPT. Label every speaker using the Cast List.
                PART 2: NOVEL CHAPTER. Write an immersive first-person story from {item['pov']}'s POV.
                
                Use '===SPLIT===' to separate Part 1 and Part 2.
                """
                
                response = model.generate_content([gf, prompt])
                st.session_state[f"res_{idx}"] = response.text.split("===SPLIT===")

        # THE SEPARATE T-BOX AND N-BOX
        if f"res_{idx}" in st.session_state:
            data = st.session_state[f"res_{idx}"]
            col_t, col_n = st.columns(2)
            
            with col_t:
                st.subheader("📜 Transcript (T-Box)")
                st.text_area("Full Dialogue", data[0], height=450, key=f"tbox_{idx}")
                
            with col_n:
                st.subheader(f"📖 {item['pov']}'s Novel (N-Box)")
                st.text_area("Narrative POV", data[1] if len(data)>1 else "", height=450, key=f"nbox_{idx}")

            # DOWNLOAD BUTTON (ONLY SHOWS AFTER PROD TO SAVE RAM)
            with open(item['file'], "rb") as f:
                st.download_button("📥 Save Episode to Phone", f, file_name=item['file'], mime="video/mp4")
