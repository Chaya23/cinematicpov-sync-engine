import os
import streamlit as st
from google import genai
from google.genai import types
import tempfile
import time

# --- CONFIGURATION ---
MODEL_NAME = "gemini-3.1-pro-preview" 

# Setup Client
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    st.error("🔑 API Key not found! Run: export GEMINI_API_KEY='your_key' in Terminal.")

def process_production(uploaded_file, url_link, pov_character, show_name):
    temp_video_path = None

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
            tfile.write(uploaded_file.read())
            temp_video_path = tfile.name
        st.info(f"🚀 Processing uploaded file: {uploaded_file.name}")
    elif url_link:
        st.info(f"🔗 Processing URL: {url_link}")
    else:
        st.error("Please provide a video file or a URL.")
        return

    # 1. Upload & Analyze
    video_file = None
    if temp_video_path:
        st.write("☁️ Sending video to Gemini 3.1 Pro Engine...")
        # FIX: Using 'file' parameter instead of 'path'
        video_file = client.files.upload(file=temp_video_path)
        
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = client.files.get(name=video_file.name)
            st.write("⏳ AI is analyzing frames... (approx 1 min)")

    # 2. Universal Research Prompt
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    )
    
    prompt = f"""
    You are a Media Research Expert and Professional Novelist.
    VIDEO SUBJECT: {show_name}
    POV CHARACTER: {pov_character}
    
    1. RESEARCH: Use Google Search to find wikis/recaps for '{show_name}'. Verify all character names and plot details.
    2. SITCOM LOGIC: If this is multi-camera footage, ignore camera cuts and focus on scene continuity.
    3. TRANSCRIPT: Provide a high-accuracy word-for-word transcript with speaker names.
    4. NOVEL: Write a chapter from {pov_character}'s perspective.
    
    Separator: Use '### NOVEL SECTION' between the transcript and story.
    """
    
    st.write(f"✍️ Generating content for {show_name}...")
    
    # Handle inputs
    contents = [prompt]
    if video_file:
        contents.append(video_file)
    elif url_link:
        contents.append(url_link)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config
    )
    
    full_text = response.text

    # 3. Output
    try:
        if "### NOVEL SECTION" in full_text:
            transcript, novel = full_text.split("### NOVEL SECTION")
        else:
            transcript, novel = full_text, "Novel section generation incomplete."

        st.subheader("🏁 Finished Production")
        st.download_button("📥 Download Transcript", transcript, file_name=f"Transcript_{show_name}.txt")
        st.download_button(f"📥 Download {pov_character} Novel", novel, file_name=f"{pov_character}_Story.txt")
    except Exception as e:
        st.error(f"Error splitting results: {e}")
        st.write(full_text)
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)

# --- UI SETUP ---
st.set_page_config(page_title="POV Cinematic Engine", page_icon="🎬")
st.title("🎬 POV Cinematic Engine")

st.markdown("""
### 📖 How to Use
1. **Name the Show**: Enter the title (e.g., *Wizards Beyond*, *The Bear*, or a YouTube Channel).
2. **Select POV**: Tell the AI whose head we should be in for the novel (e.g., *Roman*, *Carmy*, *MKBHD*).
3. **Choose Source**: Either **Upload** an MP4 file or paste a **YouTube URL**.
4. **Launch**: Click 'Start Production'.
""")

with st.sidebar:
    st.header("Settings")
    show_name = st.text_input("Show/Video Name", placeholder="e.g. Wizards Beyond Waverly Place")
    pov_character = st.text_input("POV Character", placeholder="e.g. Roman POV")
    st.info("AI: Gemini 3.1 Pro (Multimodal + Google Search)")

col1, col2 = st.columns(2)
with col1:
    uploaded_video = st.file_uploader("Upload MP4", type=["mp4", "mov"])
with col2:
    url_link = st.text_input("OR Paste Video URL", placeholder="https://youtube.com/...")

if st.button("🚀 Start Production"):
    if not show_name or not pov_character:
        st.warning("Please enter a Show Name and POV Character in the sidebar.")
    else:
        process_production(uploaded_video, url_link, pov_character, show_name)
