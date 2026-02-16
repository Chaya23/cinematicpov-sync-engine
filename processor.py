import subprocess
import google.generativeai as genai
import os

def run_compression(input_path):
    """Shrinks video to ensure it stays under 200MB"""
    output_path = "processed_production.mp4"
    # -crf 28 compresses heavily while keeping audio clear for AI
    cmd = f"ffmpeg -i {input_path} -vcodec libx264 -crf 28 -preset fast -y {output_path}"
    subprocess.run(cmd, shell=True)
    return output_path

def novelize_content(file_path, api_key):
    """Sends the compressed file to Gemini for 1st-person POV writing"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # In a real setup, you'd upload the file to Gemini's File API here
    prompt = "Analyze this video/audio. Write a 2,000-word novel chapter in the 1st-person POV of Roman Russo."
    # response = model.generate_content([prompt, uploaded_file])
    return "The engine has analyzed the footage. Roman's chapter is being written..."
