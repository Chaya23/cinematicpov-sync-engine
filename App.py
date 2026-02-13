import streamlit as st
import os, tempfile, time, random
import google.generativeai as genai
import yt_dlp
from google.api_core import exceptions

# --- 1. THE "KEEP-ALIVE" & SETUP ---
# This must come AFTER imports but BEFORE any other logic
st.set_page_config(page_title="CinematicPOV v14.2", layout="wide", page_icon="🎬")

# JavaScript to prevent Streamlit from sleeping when the tab is inactive
st.markdown(
    """
    <script>
    var lastInteracted = Date.now();
    document.addEventListener('mousemove', function() { lastInteracted = Date.now(); });
    setInterval(function() {
        if (Date.now() - lastInteracted < 10000) {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: Math.random()}, '*');
        }
    }, 5000);
    </script>
    """,
    unsafe_allow_html=True
)

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Initialize State
if "transcript" not in st.session_state: st.session_state.transcript = ""
if "novel" not in st.session_state: st.session_state.novel = ""
if "custom_chars" not in st.session_state: st.session_state.custom_chars = "Roman, Billie, Justin, Winter, Milo, Giada"

# --- 2. ENGINE UTILITIES ---
def get_active_model():
    try:
        available = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-1.5-pro']
        for p in priority:
            if p in available: return p
        return "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

def download_video(url, tmp_dir):
    out_path = os.path.join(tmp_dir, "episode.%(ext)s")
    ydl_opts = {'format': 'bestvideo[height<=480]+bestaudio/best', 'outtmpl': out_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return os.path.join(tmp_dir, "episode.mp4")

# --- 3. SIDEBAR: CHARACTER & SCENE MANAGER ---
with st.sidebar:
    st.header("🎭 Cast & POV")
    st.session_state.custom_chars = st.text_area("Edit Names:", st.session_state.custom_chars)
    char_list = [c.strip() for c in st.session_state.custom_chars.split(",")]
    
    pov_char = st.selectbox("Select POV:", char_list)
    style = st.selectbox("Style:", ["YA Novel (S.J. Maas)", "Middle Grade (Riordan)", "Gothic"])
    
    st.divider()
    st.header("🎬 Scene Priority")
    scene_focus = st.multiselect("Ensure these scenes are included:", 
                                 ["Staten Island Makeover", "Lacey Vase Break", "Stuck to Winter", "Changeling Fight"],
                                 default=["Staten Island Makeover", "Stuck to Winter"])

# --- 4. MAIN UI ---
st.title("🎬 CinematicPOV Studio v14.2")
url_input = st.text_input("Episode URL (Disney/YT/Solar):")
uploaded = st.file_uploader("OR Upload Video:", type=['mp4'])

if st.button("🚀 EXECUTE DUAL-STAGE SYNC", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            video_path = os.path.join(tmp_dir, "input.mp4")
            if uploaded:
                with open(video_path, "wb") as f: f.write(uploaded.getbuffer())
            else:
                st.info("📥 Downloading...")
                video_path = download_video(url_input, tmp_dir)

            st.info("☁️ Uploading to Vision...")
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(4)
                video_file = genai.get_file(video_file.name)

            model_id = get_active_model()
            model = genai.GenerativeModel(model_id)

            # --- STAGE 1: THE DIALOGUE (ACCURACY MODE) ---
            st.info("🎤 Stage 1: Transcribing Verbatim...")
            t_prompt = f"""
            Identify characters: {st.session_state.custom_chars}. 
            Extract EVERY line of dialogue verbatim. No summaries.
            Format: [MM:SS] Name: "Dialogue"
            """
            # Low temperature (0.1) for strict accuracy
            t_response = model.generate_content([video_file, t_prompt], generation_config={"max_output_tokens": 4000, "temperature": 0.1})
            st.session_state.transcript = t_response.text

            # --- STAGE 2: THE NOVEL (CREATIVE MODE) ---
            st.info(f"📖 Stage 2: Authoring {pov_char}'s Chapter...")
            n_prompt = f"""
            Write a first-person novel chapter from {pov_char}'s POV in {style} style.
            FOCUS SCENES: {', '.join(scene_focus)}
            
            RULES:
            1. Use the dialogue from the video.
            2. Include deep internal thoughts in italics.
            3. Describe the visual details (like the big Staten Island hair and the leopard print).
            """
            # High temperature (0.8) for creative prose
            n_response = model.generate_content([video_file, n_prompt], generation_config={"max_output_tokens": 4000, "temperature": 0.8})
            st.session_state.novel = n_response.text

            st.success("✅ Sync Complete!")
            genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Sync Interrupted: {e}")

# --- 5. STUDIO VIEW ---
if st.session_state.transcript:
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📝 Source Transcript")
        st.text_area("Script", st.session_state.transcript, height=800, key="t_disp")
    with col_r:
        st.subheader(f"📖 {pov_char}'s Chapter")
        st.text_area("Novel", st.session_state.novel, height=800, key="n_disp")
