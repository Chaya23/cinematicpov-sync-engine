import streamlit as st
import os, tempfile, time
import google.generativeai as genai
import yt_dlp

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="CinematicPOV: Masterpiece Edition", layout="wide", page_icon="✍️")

# Authentication
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 2. THE BYPASS DOWNLOADER ---
def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best', # High enough for Vision, small for speed
        'outtmpl': out_path,
        'merge_output_format': 'mp4',
        'quiet': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'proxy': st.secrets.get("PROXY_URL"),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. UI LAYOUT ---
st.title("🎬 CinematicPOV: Author Edition v12.0")
st.caption("AI Vision + Web Grounding + YA Literary Prose.")

col1, col2 = st.columns([2, 1])
with col1:
    url_input = st.text_input("Enter Episode Link (Disney/YouTube/Solar):")
    uploaded = st.file_uploader("OR Upload Video File:", type=['mp4', 'mov', 'avi'])
with col2:
    chars = ["Roman", "Billie", "Justin", "Winter", "Milo", "Giada"]
    pov_char = st.selectbox("Select POV Character:", chars)
    style = st.selectbox("Writing Style:", [
        "YA Fantasy (Sarah J. Maas style)", 
        "Snarky Middle Grade (Rick Riordan style)", 
        "Gothic Drama",
        "Standard TV Script"
    ])

# --- 4. THE CORE ENGINE ---
if st.button("🚀 AUTHOR FULL CHAPTER", type="primary"):
    if not url_input and not uploaded:
        st.warning("Please provide a source.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Step A: Download/Load
            if uploaded:
                video_path = os.path.join(tmp_dir, "input.mp4")
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading episode video...")
                video_path = download_video(url_input, tmp_dir)

            # Step B: Upload to Google Files API
            st.info("☁️ Feeding video to Gemini Vision Engine...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            # Step C: The "Agentic" Author Prompt
            st.info(f"✍️ Authoring Chapter in {style}...")
            
            # Using Gemini 3 Flash-Preview for 2026 Multimodal power
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=[{'google_search_retrieval': {}}] # Enables web search grounding
            )
            
            prompt = f"""
            SYSTEM INSTRUCTION:
            1. Use GOOGLE SEARCH to find the official 'LaughingPlace' recap or 'Disney Wiki' plot for 'Wizards Beyond Waverly Place' matching this video content.
            2. WATCH the attached video to match the EXACT dialogue to the character names.
            
            WRITING TASK:
            Write a detailed, first-person chapter from {pov_char}'s POV. 
            The length should feel substantial (like a full chapter in a novel).
            
            STYLE: {style}
            - Use deep internal monologue (italics for thoughts).
            - Focus on sensory details: the leopard print texture, the smell of 'dragon mountain' smoke, the weight of the Lacey vase.
            - Emotional Stakes: Roman's fear of his wizard life breaking his mortal friendships.
            
            FORMAT:
            ---TRANSCRIPT---
            [Exact Labeled Transcript with scene cues]
            ---POV---
            [The Full Novelized Chapter]
            """

            response = model.generate_content([video_file, prompt])
            
            # Step D: Display & Parse
            output = response.text
            if "---POV---" in output:
                parts = output.split("---POV---")
                st.session_state.transcript = parts[0].replace("---TRANSCRIPT---", "")
                st.session_state.novel = parts[1]
                st.success("✅ Masterpiece Written!")
            else:
                st.session_state.novel = output # Fallback if split fails
            
            # Cleanup
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. TABS FOR RESULTS ---
if "novel" in st.session_state:
    tab1, tab2 = st.tabs(["📖 The Manuscript", "📝 Dialogue Script"])
    with tab1:
        st.markdown(f"### {pov_char}'s Journey")
        st.write(st.session_state.novel)
        st.download_button("Save as .txt", st.session_state.novel, "chapter.txt")
    with tab2:
        st.text_area("Full Transcript Reference:", st.session_state.transcript, height=500)
