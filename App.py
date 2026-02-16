import streamlit as st
from processor import run_compression, novelize_content
import os

# Secrets Setup
API_KEY = st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="Roman's Redemption", layout="centered")
st.title("🧙‍♂️ Roman's Redemption Studio")

tab1, tab2 = st.tabs(["🔗 Link/Download", "📱 Upload DVR"])

with tab1:
    url = st.text_input("Paste Disney Now Link:")
    if st.button("Download & Process"):
        st.info("🛰️ Downloading in background. You can minimize the app now.")
        # Background download logic
        os.system(f"yt-dlp -f 'bestvideo[height<=480]+bestaudio' -o 'temp.mp4' {url}")
        compressed = run_compression("temp.mp4")
        result = novelize_content(compressed, API_KEY)
        st.success(result)

with tab2:
    up_file = st.file_uploader("Upload 4K Record", type=["mp4", "mov"])
    if up_file:
        with open("raw_up.mp4", "wb") as f:
            f.write(up_file.getbuffer())
        if st.button("Compress & Sync"):
            with st.spinner("Compressing..."):
                compressed = run_compression("raw_up.mp4")
                st.write("✅ Ready for Gemini!")
