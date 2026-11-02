import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# Page configuration
st.set_page_config(
    page_title="Voice Notes to Action Items",
    page_icon="🎙️",
    layout="wide",
)
st.title("🎙️ Voice Notes → Action Items")
st.caption("Transcribe spoken voice notes and automatically extract tasks, priorities, owners, and deadlines using Gemini.")

# Check for API key in environment or secrets
default_api_key = os.environ.get("GEMINI_API_KEY", "")
if not default_api_key:
    try:
        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_api_key = ""

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        help="Get your key from https://aistudio.google.com/"
    )
    
    model_name = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0,
        help="Fast multimodal model with audio understanding and structured JSON support."
    )
    
    st.markdown("---")
    st.markdown("💡 **Need an API Key?**")
    st.markdown("[Get one free from Google AI Studio](https://aistudio.google.com/)")

if not api_key:
    st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to proceed.")
    st.stop()

# Initialize Client
client = genai.Client(api_key=api_key)

# Structured Output Schema
class ActionItem(BaseModel):
    task: str = Field(description="The action item or task to be completed.")
    priority: str = Field(description="Priority level: High, Medium, or Low.")
    owner: Optional[str] = Field(description="Person responsible, or 'Unassigned'.")
    due_date: Optional[str] = Field(description="Deadline mentioned, or 'Not specified'.")

class ExtractionResult(BaseModel):
    transcript: str = Field(description="Full word-for-word transcript of the audio.")
    action_items: List[ActionItem] = Field(description="List of extracted tasks.")

# 1. Screen & Audio Input
st.subheader("1. Provide Audio Input")
tab1, tab2 = st.tabs(["📁 Upload Audio File", "🎤 Record Audio"])
audio_file = None

with tab1:
    uploaded = st.file_uploader(
        "Upload an audio file",
        type=["mp3", "wav", "m4a", "ogg"],
        help="Upload standard audio formats up to 200MB."
    )
    if uploaded:
        audio_file = uploaded

with tab2:
    st.info("Allow microphone access when your browser prompts. If recording fails, use the Upload tab.")
    recorded = st.audio_input(
        "Record a voice note directly",
        help="Microphone access must be allowed for this site.",
    )
    if recorded:
        audio_file = recorded

# Processing Logic
if audio_file:
    st.audio(audio_file)
    
    if st.button("🚀 Process Voice Note", type="primary", use_container_width=True):
        with st.status("Processing Audio with Gemini...", expanded=True) as status:
            try:
                status.write(f"Transcribing audio and extracting tasks using `{model_name}`...")
                prompt = """
                Listen carefully to this audio file.
                1. Provide an accurate word-for-word transcript.
                2. Extract all action items, assignees, dates, and priorities.
                If information like owner or due date is missing or ambiguous, mark it as 'Unassigned' or 'Not specified'.
                """
                
                audio_part = types.Part.from_bytes(
                    data=audio_file.getvalue(),
                    mime_type=audio_file.type or "audio/wav",
                )

                # Gemini API call with structured schema
                response = client.models.generate_content(
                    model=model_name,
                    contents=[audio_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionResult,
                    ),
                )
                
                status.update(label="Processing Complete!", state="complete", expanded=False)
                
                # Parse JSON output
                result = ExtractionResult.model_validate_json(response.text)

            except Exception as e:
                status.update(label="An error occurred", state="error", expanded=True)
                st.error(f"Error processing audio: {str(e)}")
                st.stop()

        # 2. Display Transcript
        st.subheader("2. 📝 Transcript")
        st.info(f'"{result.transcript}"')

        # 3. Display Structured Action Items
        st.subheader("3. ✅ Action Items")
        if not result.action_items:
            st.warning("No actionable tasks identified in this recording.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(result.action_items):
                col = cols[idx % 2]
                with col:
                    priority_lower = item.priority.lower()
                    color = "🔴" if priority_lower == "high" else ("🟡" if priority_lower == "medium" else "🟢")
                    
                    with st.container(border=True):
                        st.markdown(f"### {color} {item.task}")
                        st.markdown(f"**👤 Owner:** `{item.owner or 'Unassigned'}`")
                        st.markdown(f"**📅 Due Date:** `{item.due_date or 'Not specified'}`")
                        st.markdown(f"**⚡ Priority:** `{item.priority.capitalize()}`")
