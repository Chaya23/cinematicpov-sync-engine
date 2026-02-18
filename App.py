import streamlit as st
from google import genai
from google.genai import types
import subprocess
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIG & CLIENT ---
st.set_page_config(page_title="POV Cinema DVR 2026", layout="wide")

# Using Gemini 3 Pro Preview for the massive 1M+ context window
MODEL_ID = "gemini-3-pro-preview"

if "library" not in st.session_state:
    st.session_state.library = []

api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# --- 2. DYNAMIC POV & CAST SETUP ---
with st.sidebar:
    st.header("🎭 Show Production")
    show_name = st.text_input("Show:", "Wizards Beyond Waverly Place")
    
    # Character list is the master source
    cast_input = st.text_area(
        "Character List (Name: Role):", 
        "Roman: Sarcastic Wizard\nBillie: Rebellious Lead\nGiada: The Mom\nJustin: Mentor"
    )
    
    # Automatically turn the list into dropdown options
    # This prevents the "POV 0.2" error
    names = [line.split(":")[0].strip() for line in cast_input.split("\n") if ":" in line]
    if not names: names = ["Default"]
    
    pov_hero = st.selectbox("Select Narrator POV:", names)
    
    st.divider()
    c_file = st.file_uploader("🍪 Upload cookies.txt", type="txt")

# --- 3. WORD EXPORT ---
def create_docx(transcript, novel, pov, show):
    doc = Document()
    doc.add_heading(f"{show}: {pov} POV", 0)
    doc.add_heading('Verbatim Transcript', level=1); doc.add_paragraph(transcript)
    doc.add_page_break()
    doc.add_heading('Deep POV Novel', level=1); doc.add_paragraph(novel)
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# --- 4. PRODUCTION ENGINE ---
st.title(f"🎬 {show_name} Studio")
link = st.text_input("Paste Video Link (Disney+/Netflix):")

if st.button("🚀 Record Episode") and link:
    fn = f"master_{datetime.now().strftime('%H%M%S')}.mp4"
    # Use H.264 for mobile stability
    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", fn, link]
    if c_file:
        with open("c.txt", "wb") as f: f.write(c_file.getbuffer())
        cmd.extend(["--cookies", "c.txt"])
    
    with st.status("🎬 DVR Recording..."):
        subprocess.run(cmd)
    
    if os.path.exists(fn):
        st.session_state.library.append({"file": fn, "show": show_name, "cast": cast_input, "pov": pov_hero})
        st.rerun()

# --- 5. THE AI ANALYSIS (UNLIMITED TOKENS FIX) ---
for idx, item in enumerate(st.session_state.library):
    with st.container(border=True):
        st.write(f"🎞️ **{item['file']}** | **POV:** {item['pov']}")
        
        if st.button("✨ Start Full Production", key=f"ai_{idx}"):
            with st.status("🧠 Gemini 3 Pro is processing 24 minutes..."):
                try:
                    file_upload = client.files.upload(file=item['file'])
                    while file_upload.state == "PROCESSING":
                        time.sleep(3)
                        file_upload = client.files.get(name=file_upload.name)

                    # ✅ THE FIX: Setting max_output_tokens to 65k to prevent the 400 error
                    # Also using the Google Search tool for name accuracy
                    config = types.GenerateContentConfig(
                        max_output_tokens=65536,
                        temperature=0.7,
                        tools=[types.Tool(google_search={})]
                    )

                    prompt = f"""
                    1. Search Google for the official episode recap of '{item['show']}' to ensure character and plot accuracy.
                    2. Watch the video. Provide a FULL VERBATIM TRANSCRIPT. Do not skip any dialogue. 
                       Identify characters correctly based on: {item['cast']}.
                    3. Write a Deep POV Novel chapter from {item['pov']}'s perspective.
                    Format: [TRANSCRIPT] ... [END TRANSCRIPT] and [NOVEL] ... [END NOVEL]
                    """

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[file_upload, prompt],
                        config=config
                    )
                    st.session_state[f"res_{idx}"] = response.text
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- DISPLAY & EXPORT ---
        if f"res_{idx}" in st.session_state:
            res = st.session_state[f"res_{idx}"]
            # Helper to split parts
            try:
                t = res.split("[TRANSCRIPT]")[1].split("[END TRANSCRIPT]")[0].strip()
                n = res.split("[NOVEL]")[1].split("[END NOVEL]")[0].strip()
            except:
                t, n = res, "Error splitting sections. Check Transcript box."

            c1, c2 = st.columns(2)
            c1.text_area("📜 Full Transcript", t, height=500)
            c2.text_area(f"📖 {item['pov']}'s Novel", n, height=500)
            
            st.download_button("📄 Download .docx", create_docx(t, n, item['pov'], item['show']), file_name=f"{item['pov']}_Script.docx")
