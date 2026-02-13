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
# --- Add this updated Stage 1 & 2 logic to your code ---

# STAGE 1: THE VERBATIM SCRIPT
# We change the prompt to be a "Dictation" task, which prevents the AI from summarizing.
st.info("🎤 Stage 1: Running High-Accuracy Dictation...")
t_prompt = f"""
ACT AS: A professional court reporter.
CAST: {st.session_state.custom_chars}

TASK:
1. Watch the video and list every speaker change.
2. Provide the EXACT dialogue. Do not summarize.
3. Use the format: [MM:SS] Name: "Dialogue"

START TRANSCRIPT:
"""
# We use a lower temperature (0.1) for the transcript to prevent 'hallucinations'
t_response = model.generate_content([video_file, t_prompt], generation_config={"max_output_tokens": 5000, "temperature": 0.1})
st.session_state.transcript = t_response.text

# STAGE 2: THE "SCENE-STAY" NOVEL
# We tell the AI NOT to skip time. It must cover the 'Staten Island' makeover.
st.info(f"📖 Stage 2: Authoring Roman's Chapter...")
n_prompt = f"""
STORY TASK:
Write a first-person chapter from {pov_char}'s POV in {style} style.

CRITICAL SCENES TO COVER:
- The tension at breakfast with the missing magic.
- Billie and Giada's leopard-print 'Staten Island' makeover (Roman's reaction to the big hair).
- The shattering of the Lacey vase.
- The physical fusion/stuck-together moment with Winter.

WRITING RULE: Do not summarize the episode. Write it scene-by-scene with dialogue woven in.
"""
n_response = model.generate_content([video_file, n_prompt], generation_config={"max_output_tokens": 5000, "temperature": 0.8})
st.session_state.novel = n_response.text
