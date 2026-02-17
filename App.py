                    ydl_cmd.extend(["--cookies", "cookies.txt"])
                subprocess.run(ydl_cmd, check=True)

            gem_file = genai.upload_file(path=source)
            while gem_file.state.name == "PROCESSING":
                time.sleep(3)
                gem_file = genai.get_file(gem_file.name)

            # --- THE "INTEGRITY" FIX ---
            # We use a simple list of strings which is more stable for the current API
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Identify characters via visual grounding. Narrator: {pov_choice}.
            CAST BIBLE: {cast_info}
            TASK 1: VERBATIM TRANSCRIPT (Tag speakers accurately).
            ---SPLIT---
            TASK 2: 2500-WORD NOVEL CHAPTER from POV of {pov_choice}.
            """
            
            response = model.generate_content([gem_file, prompt], safety_settings=safety_settings)

            if response.text:
                parts = response.text.split("---SPLIT---")
                st.session_state.transcript = parts[0].strip() if len(parts) > 0 else ""
                st.session_state.chapter = parts[1].strip() if len(parts) > 1 else ""
                st.rerun()

        except Exception as e:
            st.error(f"Studio Error: {e}")

# 5. RESULTS HUB
if st.session_state.transcript or st.session_state.chapter:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 Verbatim Transcript")
        st.download_button("📥 Export Transcript (Word)", create_docx("Transcript", st.session_state.transcript), "Transcript.docx")
        st.text_area("T-Box", st.session_state.transcript, height=550)
    with col2:
        st.subheader(f"📖 {pov_choice}'s Chapter")
        st.download_button("📥 Export Novel (Word)", create_docx("Novel Chapter", st.session_state.chapter), "Novel.docx")
        st.text_area("N-Box", st.session_state.chapter, height=550)
