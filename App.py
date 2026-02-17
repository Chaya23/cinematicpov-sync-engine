import streamlit as st
import google.generativeai as genai
import subprocess
import os
import time
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="POV Cinema DVR", layout="wide", page_icon="🎬")

# ⚠️ FIX: Switched to the confirmed stable model for 2026
MODEL_NAME = "gemini-2.0-flash"

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. SIDEBAR: DIAGNOSTICS & SETTINGS ---
with st.sidebar:
    st.header("⚙️ Studio Settings")
    
    # SYSTEM DIAGNOSTIC (Fixes the 404 mystery)
    if st.button("🔍 Check My Available Models"):
        try:
            st.write("Your API Key has access to:")
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    st.code(m.name)
        except Exception as e:
            st.error(f"API Error: {e}")

    st.divider()
    
    # CAST & POV EDITOR
    st.subheader("🎭 Show Config")
    show_title = st.text_input("Show Title", "Wizards Beyond Waverly Place")
    
    # Dynamic Cast List
    cast_raw = st.text_area(
        "Edit Cast (Comma separated)", 
        "Roman, Billie, Justin, Milo, Winter, Giada"
    )
    cast_list = [x.strip() for x in cast_raw.split(",") if x.strip()]
    
    # The POV Dropdown
    pov_hero = st.selectbox("Narrator POV:", cast_list)

    st.divider()
    
    # COOKIE LOADER
    st.subheader("🍪 Disney+/Netflix Access")
    c_file = st.file_uploader("Upload cookies.txt", type="txt")

# --- 3. DVR ENGINE (H.264 SAFE MODE) ---
def dvr_download(url, cookies=None):
    ts = datetime.now().strftime("%H%M%S")
    fn = f"episode_{ts}.mp4"
    
    # Force mobile-compatible video format
    cmd = [
        "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4", "-o", fn, url
    ]
    
    if cookies:
        with open("cookies.txt", "wb") as f:
            f.write(cookies.getbuffer())
        cmd.extend(["--cookies", "cookies.txt"])

    with st.status(f"🎬 Recording {show_title}..."):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            return fn
        st.error(f"DVR Failed: {p.stderr}")
        return None

# --- 4. MAIN STUDIO ---
st.title(f"🎬 {show_title} Production Studio")

u_input = st.text_input(f"Paste {show_title} Link:")

if st.button("🚀 Record Episode", use_container_width=True):
    if u_input:
        vid = dvr_download(u_input, c_file)
        if vid:
            st.session_state.library.append({
                "file": vid,
                "pov": pov_hero,
                "cast": cast_raw,
                "show": show_title
            })
            st.rerun()

# --- 5. LIBRARY & AI PROCESSOR ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['show']}** (POV: {item['pov']})")
        
        # AI ANALYSIS BUTTON
        if st.button(f"✨ Run Production (Gemini 2.0)", key=f"run_{idx}"):
            with st.status("🧠 AI is watching the full episode..."):
                try:
                    # 1. Upload Video
                    gf = genai.upload_file(item['file'])
                    while gf.state.name == "PROCESSING":
                        time.sleep(2)
                        gf = genai.get_file(gf.name)
                    
                    # 2. Generate Content
                    model = genai.GenerativeModel(MODEL_NAME)
                    
                    # The "Anti-Cutoff" Prompt
                    prompt = f"""
                    VIDEO CONTEXT: Full episode of {item['show']}.
                    CAST CHARACTERS: {item['cast']}
                    
                    TASK 1: Write a VERBATIM TRANSCRIPT. Label speakers correctly.
                    TASK 2: Write a Novel Chapter from {item['pov']}'s POV.
                    
                    SEPARATOR: Use '===SPLIT===' between Transcript and Novel.
                    """
                    
                    response = model.generate_content([gf, prompt])
                    st.session_state[f"prod_{idx}"] = response.text.split("===SPLIT===")
                    
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # DISPLAY RESULTS (T-Box & N-Box)
        if f"prod_{idx}" in st.session_state:
            res = st.session_state[f"prod_{idx}"]
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📜 Transcript (T-Box)")
                st.text_area("Dialogue", res[0], height=500, key=f"tb_{idx}")
            with c2:
                st.subheader(f"📖 {item['pov']}'s Novel (N-Box)")
                st.text_area("Narrative", res[1] if len(res)>1 else "", height=500, key=f"nb_{idx}")

            # DOWNLOAD BUTTON (Safe Mode)
            with open(item['file'], "rb") as f:
                st.download_button("📥 Save MP4", f, file_name=item['file'], mime="video/mp4")
