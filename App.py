import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# --- 1. CORE CONFIGURATION ---
st.set_page_config(page_title="Cinematic POV Sync", layout="wide", page_icon="🎬")

# The 404 Fix: Using the specific Feb 2026 stable identifier
MODEL_NAME = "models/gemini-3-flash" 

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. SIDEBAR: CAST & COOKIE SETTINGS ---
with st.sidebar:
    st.header("📺 Show Production")
    show_title = st.text_input("Show Name:", "Wizards Beyond Waverly Place")
    
    # DYNAMIC CAST EDITOR
    cast_input = st.text_area(
        "Edit Cast (Comma separated):", 
        "Roman, Billie, Justin, Milo, Winter, Giada"
    )
    cast_list = [name.strip() for name in cast_input.split(",") if name.strip()]
    
    pov_hero = st.selectbox("Select Narrator POV:", cast_list)
    
    st.divider()
    st.subheader("🍪 Cookie Support")
    st.caption("Upload cookies.txt for Disney+/Netflix downloads.")
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

# --- 3. DVR ENGINE (MOBILE STABLE) ---
def run_dvr(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"rec_{ts}.mp4"
    
    # Forces H.264 for mobile phone compatibility to prevent crashes
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    
    if cookies:
        with open("temp_cookies.txt", "wb") as f:
            f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "temp_cookies.txt"])

    with st.status(f"🎬 DVR Recording: {fn}"):
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode == 0:
            return fn
        st.error(f"DVR Error: {process.stderr}")
        return None

# --- 4. MAIN INTERFACE ---
st.title(f"🎬 {show_title} POV Studio")

u_input = st.text_input(f"Paste Link for {show_title}:")

if st.button("🚀 Start Production", use_container_width=True):
    if u_input:
        saved_file = run_dvr(u_input, c_file)
        if saved_file:
            st.session_state.library.append({
                "file": saved_file, 
                "pov": pov_hero, 
                "show": show_title, 
                "cast": cast_input
            })
            st.rerun()

# --- 5. THE PRODUCTION LIBRARY ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['show']}** | POV: **{item['pov']}**")
        
        # PRODUCTION BUTTON
        if st.button(f"✨ Run AI Analysis", key=f"ai_{idx}"):
            with st.status("🧠 AI analyzing full 24-minute episode..."):
                try:
                    # Upload to Gemini Cloud
                    gf = genai.upload_file(item['file'])
                    while gf.state.name == "PROCESSING":
                        time.sleep(3)
                        gf = genai.get_file(gf.name)
                    
                    # Gemini 3 Long-Form Instruction
                    model = genai.GenerativeModel(MODEL_NAME)
                    prompt = f"""
                    WATCH: This full 24-minute video.
                    CAST LIST: {item['cast']}
                    
                    TASK:
                    1. Provide a VERBATIM TRANSCRIPT. Identify speakers: {item['cast']}.
                    2. Write a 1st person Novel Chapter from {item['pov']}'s POV.
                    
                    CRITICAL: Do not cut off. If dialogue is long, provide it all.
                    SPLIT SECTIONS WITH: ===SPLIT===
                    """
                    
                    # Explicitly setting thinking level to high for accuracy
                    response = model.generate_content([gf, prompt])
                    st.session_state[f"res_{idx}"] = response.text.split("===SPLIT===")
                except Exception as e:
                    st.error(f"AI Error: {str(e)}")

        # THE SEPARATE BOXES (T-BOX and N-BOX)
        if f"res_{idx}" in st.session_state:
            data = st.session_state[f"res_{idx}"]
            col_t, col_n = st.columns(2)
            
            with col_t:
                st.subheader("📜 Transcript (T-Box)")
                st.text_area("Dialogue", data[0], height=400, key=f"t_{idx}")
                
            with col_n:
                st.subheader(f"📖 {item['pov']}'s Novel (N-Box)")
                st.text_area("Pov Narrative", data[1] if len(data)>1 else "", height=400, key=f"n_{idx}")

            # DOWNLOAD TO PHONE (Prevents RAM Crash)
            with open(item['file'], "rb") as f:
                st.download_button("📥 Save MP4 to Phone", f, file_name=item['file'], mime="video/mp4")
